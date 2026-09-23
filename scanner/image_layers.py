"""
scanner/image_layers.py — Container image and layer unpacking engine (CNT feature).

Parses OCI image tarballs (docker save) and OCI layout directories, extracts
individual layers, enforces size limits and path-traversal safety, and resolves
whiteouts (.wh.*) to construct the effective filesystem view.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional


@dataclass(frozen=True)
class ExtractedLayer:
    image_digest: str
    layer_digest: str
    layer_index: int
    root: Path
    size_bytes: int


@dataclass(frozen=True)
class ExtractedImage:
    image_digest: str
    layers: tuple[ExtractedLayer, ...]
    merged_root: Path
    _temp_dir: str = ""
    _file_layer_map: dict[str, ExtractedLayer] = None  # type: ignore[assignment]


class ImageLayoutError(ValueError):
    """Raised when an image archive or layout is invalid or missing required metadata."""
    pass


class ImageSizeLimitExceeded(ImageLayoutError):
    """Raised when total extracted image size exceeds the configured max_bytes limit."""
    pass


def _warn(msg: str) -> None:
    print(f"[warn] {msg}", file=sys.stderr)


def _compute_sha256(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _compute_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def _is_safe_tar_path(name: str) -> bool:
    """Validate that tar entry path is relative and does not escape via '..' components."""
    p = Path(name)
    if p.is_absolute():
        return False
    for part in p.parts:
        if part in ("..", "/", "\\"):
            return False
        if ":" in part and os.name == "nt":  # Windows drive stream/specifier
            return False
    return True


def _extract_tar_layer(
    layer_tar_stream: tarfile.TarFile,
    dest_dir: Path,
    max_bytes: int,
    current_total_bytes: int,
    layer_label: str,
) -> tuple[int, int]:
    """Safely extract entries from a tar layer into dest_dir.

    Returns (extracted_layer_bytes, updated_total_bytes).
    Raises ImageSizeLimitExceeded if max_bytes is exceeded.
    """
    layer_bytes = 0
    total_bytes = current_total_bytes

    for member in layer_tar_stream.getmembers():
        if not _is_safe_tar_path(member.name):
            _warn(f"Refusing path traversal in layer {layer_label}: {member.name}")
            continue

        target_path = (dest_dir / member.name).resolve()
        # Verify resolved target is inside dest_dir
        if not str(target_path).startswith(str(dest_dir.resolve())):
            _warn(f"Refusing path traversal in layer {layer_label}: {member.name}")
            continue

        if member.isdir():
            target_path.mkdir(parents=True, exist_ok=True)
        elif member.isfile():
            member_size = member.size
            if total_bytes + member_size > max_bytes:
                raise ImageSizeLimitExceeded(
                    f"Image extraction exceeded size limit of {max_bytes} bytes "
                    f"at layer {layer_label} file {member.name}"
                )
            target_path.parent.mkdir(parents=True, exist_ok=True)
            f_in = layer_tar_stream.extractfile(member)
            if f_in is not None:
                with open(target_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            layer_bytes += member_size
            total_bytes += member_size
        elif member.issym() or member.islnk():
            # For symlinks inside layer, ensure parent exists
            target_path.parent.mkdir(parents=True, exist_ok=True)
            # We don't follow link, but record it if needed

    return layer_bytes, total_bytes


def _build_merged_view(
    layers: list[ExtractedLayer],
    merged_root: Path,
) -> dict[str, ExtractedLayer]:
    """Merge extracted layers from bottom (layer 0) to top (layer N-1), handling whiteouts.

    Returns a mapping of rel_path -> ExtractedLayer for each surviving file.
    """
    file_layer_map: dict[str, ExtractedLayer] = {}

    for layer in layers:
        layer_root = layer.root
        if not layer_root.exists():
            continue

        # Walk layer files
        for dirpath, dirnames, filenames in os.walk(layer_root):
            rel_dir = Path(dirpath).relative_to(layer_root)
            dest_dir = merged_root / rel_dir

            # Check for opaque whiteout in directory (.wh..wh..opq)
            if ".wh..wh..opq" in filenames:
                # Opaque whiteout: delete all pre-existing files/subdirs in dest_dir
                if dest_dir.exists():
                    for item in list(dest_dir.iterdir()):
                        if item.is_file() or item.is_symlink():
                            item.unlink(missing_ok=True)
                            rel_item = (rel_dir / item.name).as_posix()
                            file_layer_map.pop(rel_item, None)
                        elif item.is_dir():
                            shutil.rmtree(item, ignore_errors=True)
                            # Remove map entries under this dir
                            prefix = (rel_dir / item.name).as_posix() + "/"
                            for k in list(file_layer_map.keys()):
                                if k.startswith(prefix):
                                    file_layer_map.pop(k, None)

            dest_dir.mkdir(parents=True, exist_ok=True)

            for fname in filenames:
                if fname == ".wh..wh..opq":
                    continue
                if fname.startswith(".wh."):
                    # Specific file whiteout (.wh.<target>)
                    deleted_name = fname[4:]
                    target_file = dest_dir / deleted_name
                    if target_file.exists():
                        if target_file.is_dir():
                            shutil.rmtree(target_file, ignore_errors=True)
                        else:
                            target_file.unlink(missing_ok=True)
                    rel_deleted = (rel_dir / deleted_name).as_posix()
                    file_layer_map.pop(rel_deleted, None)
                    continue

                src_file = Path(dirpath) / fname
                dest_file = dest_dir / fname

                # Copy file to merged view
                if src_file.is_file() and not src_file.is_symlink():
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dest_file)
                    rel_path = (rel_dir / fname).as_posix()
                    file_layer_map[rel_path] = layer

    return file_layer_map


def _open_tar_image(tar_path: Path, max_bytes: int) -> ExtractedImage:
    """Open and unpack a docker-save formatted tar archive."""
    temp_dir = tempfile.mkdtemp(prefix="ecdat_cnt_")
    temp_path = Path(temp_dir)

    try:
        with tarfile.open(tar_path, "r:*") as outer_tar:
            # Check for manifest.json or index.json
            names = set(outer_tar.getnames())
            if "manifest.json" not in names and "index.json" not in names:
                raise ImageLayoutError(
                    f"Invalid container image tarball '{tar_path}': "
                    f"missing manifest.json or index.json"
                )

            total_bytes = 0
            image_digest = "sha256:unknown"
            layers: list[ExtractedLayer] = []

            if "manifest.json" in names:
                manifest_f = outer_tar.extractfile("manifest.json")
                if manifest_f is None:
                    raise ImageLayoutError("Cannot read manifest.json from image tarball")
                manifest_data = json.load(manifest_f)
                if not isinstance(manifest_data, list) or len(manifest_data) == 0:
                    raise ImageLayoutError("Empty or malformed manifest.json in image tarball")

                img_entry = manifest_data[0]
                config_blob_name = img_entry.get("Config", "")
                if config_blob_name and config_blob_name in names:
                    cfg_f = outer_tar.extractfile(config_blob_name)
                    if cfg_f is not None:
                        image_digest = _compute_sha256(cfg_f.read())
                if image_digest == "sha256:unknown":
                    image_digest = _compute_file_sha256(tar_path)

                layer_paths = img_entry.get("Layers", [])
                for idx, layer_tar_name in enumerate(layer_paths):
                    if layer_tar_name not in names:
                        continue
                    layer_f = outer_tar.extractfile(layer_tar_name)
                    if layer_f is None:
                        continue

                    layer_digest = _compute_sha256(Path(layer_tar_name).name.encode("utf-8"))
                    # If layer name is like <hash>/layer.tar or <hash>.tar, use hash
                    base_name = Path(layer_tar_name).parts[0] if len(Path(layer_tar_name).parts) > 1 else Path(layer_tar_name).stem
                    if len(base_name) == 64 and all(c in "0123456789abcdefABCDEF" for c in base_name):
                        layer_digest = f"sha256:{base_name.lower()}"

                    layer_dir = temp_path / f"layer_{idx}"
                    layer_dir.mkdir(parents=True, exist_ok=True)

                    with tarfile.open(fileobj=layer_f, mode="r:*") as inner_tar:
                        l_bytes, total_bytes = _extract_tar_layer(
                            inner_tar, layer_dir, max_bytes, total_bytes, layer_digest
                        )

                    layers.append(
                        ExtractedLayer(
                            image_digest=image_digest,
                            layer_digest=layer_digest,
                            layer_index=idx,
                            root=layer_dir,
                            size_bytes=l_bytes,
                        )
                    )

            elif "index.json" in names:
                # OCI image archive
                index_f = outer_tar.extractfile("index.json")
                if index_f is None:
                    raise ImageLayoutError("Cannot read index.json from image archive")
                index_data = json.load(index_f)
                manifests = index_data.get("manifests", [])
                if not manifests:
                    raise ImageLayoutError("No manifests in OCI index.json")

                manifest_desc = manifests[0]
                image_digest = manifest_desc.get("digest", _compute_file_sha256(tar_path))
                m_digest = manifest_desc.get("digest", "")
                m_blob_name = f"blobs/sha256/{m_digest.split(':')[-1]}" if ":" in m_digest else m_digest

                if m_blob_name in names:
                    m_f = outer_tar.extractfile(m_blob_name)
                    if m_f is not None:
                        m_data = json.load(m_f)
                        layer_descs = m_data.get("layers", [])
                        for idx, l_desc in enumerate(layer_descs):
                            l_digest = l_desc.get("digest", f"sha256:layer{idx}")
                            l_blob = f"blobs/sha256/{l_digest.split(':')[-1]}" if ":" in l_digest else l_digest
                            if l_blob not in names:
                                continue
                            l_f = outer_tar.extractfile(l_blob)
                            if l_f is None:
                                continue
                            layer_dir = temp_path / f"layer_{idx}"
                            layer_dir.mkdir(parents=True, exist_ok=True)
                            with tarfile.open(fileobj=l_f, mode="r:*") as inner_tar:
                                l_bytes, total_bytes = _extract_tar_layer(
                                    inner_tar, layer_dir, max_bytes, total_bytes, l_digest
                                )
                            layers.append(
                                ExtractedLayer(
                                    image_digest=image_digest,
                                    layer_digest=l_digest,
                                    layer_index=idx,
                                    root=layer_dir,
                                    size_bytes=l_bytes,
                                )
                            )

            merged_root = temp_path / "merged"
            merged_root.mkdir(parents=True, exist_ok=True)
            file_layer_map = _build_merged_view(layers, merged_root)

            return ExtractedImage(
                image_digest=image_digest,
                layers=tuple(layers),
                merged_root=merged_root,
                _temp_dir=temp_dir,
                _file_layer_map=file_layer_map,
            )

    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def _open_oci_dir(layout_dir: Path, max_bytes: int) -> ExtractedImage:
    """Open an unpacked OCI layout directory."""
    index_file = layout_dir / "index.json"
    if not index_file.is_file():
        raise ImageLayoutError(f"Not an OCI image-layout directory: missing {index_file}")

    try:
        index_data = json.loads(index_file.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ImageLayoutError(f"Failed to parse index.json: {exc}")

    manifests = index_data.get("manifests", [])
    if not manifests:
        raise ImageLayoutError("No manifests listed in index.json")

    manifest_desc = manifests[0]
    m_digest = manifest_desc.get("digest", "")
    image_digest = m_digest or f"sha256:{hashlib.sha256(index_file.read_bytes()).hexdigest()}"

    temp_dir = tempfile.mkdtemp(prefix="ecdat_cnt_oci_")
    temp_path = Path(temp_dir)

    try:
        blobs_dir = layout_dir / "blobs" / "sha256"
        m_hex = m_digest.split(":")[-1] if ":" in m_digest else m_digest
        m_file = blobs_dir / m_hex
        if not m_file.is_file():
            raise ImageLayoutError(f"Manifest blob not found: {m_file}")

        m_data = json.loads(m_file.read_text(encoding="utf-8"))
        layer_descs = m_data.get("layers", [])
        layers: list[ExtractedLayer] = []
        total_bytes = 0

        for idx, l_desc in enumerate(layer_descs):
            l_digest = l_desc.get("digest", f"sha256:layer_{idx}")
            l_hex = l_digest.split(":")[-1] if ":" in l_digest else l_digest
            l_tar_file = blobs_dir / l_hex

            layer_dir = temp_path / f"layer_{idx}"
            layer_dir.mkdir(parents=True, exist_ok=True)
            l_bytes = 0

            if l_tar_file.is_file():
                with tarfile.open(l_tar_file, mode="r:*") as inner_tar:
                    l_bytes, total_bytes = _extract_tar_layer(
                        inner_tar, layer_dir, max_bytes, total_bytes, l_digest
                    )

            layers.append(
                ExtractedLayer(
                    image_digest=image_digest,
                    layer_digest=l_digest,
                    layer_index=idx,
                    root=layer_dir,
                    size_bytes=l_bytes,
                )
            )

        merged_root = temp_path / "merged"
        merged_root.mkdir(parents=True, exist_ok=True)
        file_layer_map = _build_merged_view(layers, merged_root)

        return ExtractedImage(
            image_digest=image_digest,
            layers=tuple(layers),
            merged_root=merged_root,
            _temp_dir=temp_dir,
            _file_layer_map=file_layer_map,
        )

    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def open_image(image_path: Path, *, max_bytes: int) -> ExtractedImage:
    """Open and extract a container image tarball or OCI layout directory.

    Enforces max_bytes limit and path-traversal safety.
    """
    p = Path(image_path).resolve()
    if not p.exists():
        raise ImageLayoutError(f"Image path does not exist: {p}")

    if p.is_file():
        return _open_tar_image(p, max_bytes)
    elif p.is_dir():
        return _open_oci_dir(p, max_bytes)
    else:
        raise ImageLayoutError(f"Unsupported image path type: {p}")


def iter_files(image: ExtractedImage) -> Iterator[tuple[ExtractedLayer, Path]]:
    """Yield (layer, file_path_in_merged_root) for each file in the merged view.

    The returned layer is the one that contributed this file to the merged view.
    """
    merged_root = image.merged_root
    file_map = image._file_layer_map or {}
    default_layer = image.layers[-1] if image.layers else ExtractedLayer(image.image_digest, "sha256:unknown", 0, merged_root, 0)

    for dirpath, dirnames, filenames in os.walk(merged_root):
        for fname in sorted(filenames):
            fpath = Path(dirpath) / fname
            if fpath.is_file() and not fpath.is_symlink():
                rel_path = fpath.relative_to(merged_root).as_posix()
                layer = file_map.get(rel_path, default_layer)
                yield (layer, fpath)


def cleanup(image: ExtractedImage) -> None:
    """Clean up extracted temporary directories for the image."""
    if image._temp_dir and Path(image._temp_dir).exists():
        shutil.rmtree(image._temp_dir, ignore_errors=True)
