
import java.security.MessageDigest;
import javax.crypto.Cipher;
import java.security.KeyPairGenerator;
import java.security.Signature;

public class SecurityManager {

    // WEAK: MD5 hashing
    public byte[] hashMD5(String data) throws Exception {
        MessageDigest md = MessageDigest.getInstance("MD5");
        return md.digest(data.getBytes());
    }

    // WEAK: SHA1 hashing
    public byte[] hashSHA1(String data) throws Exception {
        MessageDigest md = MessageDigest.getInstance("SHA-1");
        return md.digest(data.getBytes());
    }

    // OK: SHA-256 hashing
    public byte[] hashSHA256(String data) throws Exception {
        MessageDigest md = MessageDigest.getInstance("SHA-256");
        return md.digest(data.getBytes());
    }

    // WEAK: DES encryption
    public byte[] encryptDES(byte[] data, byte[] key) throws Exception {
        Cipher cipher = Cipher.getInstance("DES/ECB/PKCS5Padding");
        cipher.init(Cipher.ENCRYPT_MODE, new javax.crypto.spec.SecretKeySpec(key, "DES"));
        return cipher.doFinal(data);
    }

    // WEAK: 3DES encryption
    public byte[] encrypt3DES(byte[] data, byte[] key) throws Exception {
        Cipher cipher = Cipher.getInstance("DESede/ECB/PKCS5Padding");
        cipher.init(Cipher.ENCRYPT_MODE, new javax.crypto.spec.SecretKeySpec(key, "DESede"));
        return cipher.doFinal(data);
    }

    // WEAK: RC4 encryption
    public byte[] encryptRC4(byte[] data, byte[] key) throws Exception {
        Cipher cipher = Cipher.getInstance("RC4");
        cipher.init(Cipher.ENCRYPT_MODE, new javax.crypto.spec.SecretKeySpec(key, "RC4"));
        return cipher.doFinal(data);
    }

    // OK: AES encryption
    public byte[] encryptAES(byte[] data, byte[] key) throws Exception {
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, new javax.crypto.spec.SecretKeySpec(key, "AES"));
        return cipher.doFinal(data);
    }

    // WEAK: RSA key generation with small size
    public java.security.KeyPair generateRSA1024() throws Exception {
        KeyPairGenerator kpg = KeyPairGenerator.getInstance("RSA");
        kpg.initialize(1024);
        return kpg.generateKeyPair();
    }

    // OK: RSA key generation
    public java.security.KeyPair generateRSA2048() throws Exception {
        KeyPairGenerator kpg = KeyPairGenerator.getInstance("RSA");
        kpg.initialize(2048);
        return kpg.generateKeyPair();
    }

    // WEAK: DSA signatures
    public byte[] signDSA(byte[] data, java.security.PrivateKey key) throws Exception {
        Signature sig = Signature.getInstance("SHA1withDSA");
        sig.initSign(key);
        sig.update(data);
        return sig.sign();
    }
}
