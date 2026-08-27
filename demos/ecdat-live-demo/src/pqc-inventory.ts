import { createHash, generateKeyPair } from "node:crypto";

export const documentDigest = createHash("sha256").update("demo").digest("hex");
generateKeyPair("rsa", { modulusLength: 2048 }, () => {});
