
// WEAK: MD5 digest using Web Crypto API
async function hashMD5(data: BufferSource): Promise<ArrayBuffer> {
    const crypto = window.crypto;
    return crypto.subtle.digest("MD5", data);
}

// WEAK: SHA1 digest
async function hashSHA1(data: BufferSource): Promise<ArrayBuffer> {
    const crypto = globalThis.crypto;
    return crypto.subtle.digest("SHA-1", data);
}

// OK: SHA256 digest
async function hashSHA256(data: BufferSource): Promise<ArrayBuffer> {
    const crypto = window.crypto;
    return crypto.subtle.digest("SHA-256", data);
}

// WEAK: RC4 using Node crypto
const crypto = require("crypto");
function encryptRC4(key: Buffer, data: Buffer): Buffer {
    return crypto.createCipheriv("rc4", key, Buffer.alloc(0));
}
