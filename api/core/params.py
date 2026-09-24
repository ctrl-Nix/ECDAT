"""Shared, typed query parameters for analyst list endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Query


@dataclass(frozen=True)
class FindingListParams:
    risk_tier: list[str] | None
    primitive: list[str] | None
    algorithm: list[str] | None
    language: list[str] | None
    sort_by: str | None
    sort_dir: str
    limit: int
    offset: int


def common_list_params(
    risk_tier: Annotated[
        list[str] | None,
        Query(description="Repeat for OR-within-category, e.g. ?risk_tier=CRITICAL&risk_tier=HIGH"),
    ] = None,
    primitive: Annotated[list[str] | None, Query()] = None,
    algorithm: Annotated[list[str] | None, Query()] = None,
    language: Annotated[list[str] | None, Query()] = None,
    sort_by: Annotated[
        str | None,
        Query(pattern="^(risk_tier|algorithm|primitive|language|file|line)$"),
    ] = None,
    sort_dir: Annotated[str, Query(pattern="^(asc|desc)$")] = "asc",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> FindingListParams:
    return FindingListParams(
        risk_tier=risk_tier,
        primitive=primitive,
        algorithm=algorithm,
        language=language,
        sort_by=sort_by,
        sort_dir=sort_dir,
        limit=limit,
        offset=offset,
    )
