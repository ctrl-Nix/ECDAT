
const crypto = require("crypto");

// WEAK: MD5 hashing
function hashPasswordMD5(password) {
    return crypto.createHash("md5").update(password).digest("hex");
}

// WEAK: SHA1 hashing
function hashPasswordSHA1(password) {
    return crypto.createHash("sha1").update(password).digest("hex");
}

// OK: SHA256 hashing
function hashPasswordSHA256(password) {
    return crypto.createHash("sha256").update(password).digest("hex");
}

// WEAK: MD5 HMAC
function createHmacMD5(key, message) {
    return crypto.createHmac("md5", key).update(message).digest("hex");
}

// WEAK: DES encryption
function encryptDES(key, data) {
    return crypto.createCipher("des", key).update(data, "utf8", "hex");
}

// WEAK: RC4 encryption
function encryptRC4(key, data) {
    return crypto.createCipher("rc4", key).update(data, "utf8", "hex");
}

// OK: AES encryption
function encryptAES(key, data) {
    return crypto.createCipheriv("aes-256-gcm", key, crypto.randomBytes(12));
}

// WEAK: RSA key generation with small size
function generateRSAKeyPair() {
    return crypto.generateKeyPairSync("rsa", { modulusLength: 1024 });
}

// OK: RSA key generation
function generateRSAKeyPairStrong() {
    return crypto.generateKeyPairSync("rsa", { modulusLength: 4096 });
}

// OK: ECC key generation
function generateECCKeyPair() {
    return crypto.generateKeyPairSync("ec", { namedCurve: "prime256v1" });
}
