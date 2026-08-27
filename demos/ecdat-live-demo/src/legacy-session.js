// Deliberately weak demo code. Never use these algorithms in production.
const crypto = require("node:crypto");

const sessionDigest = crypto.createHash("md5").update("demo").digest("hex");
const legacyKey = crypto.createCipheriv("des-ede3-cbc", Buffer.alloc(24), Buffer.alloc(8));

// This decoy must not be reported: it is not an imported crypto module.
const localCrypto = { createHash: () => "not a cryptographic primitive" };
localCrypto.createHash("md5");

module.exports = { sessionDigest, legacyKey };
