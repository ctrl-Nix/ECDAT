// Deliberately weak demo code. Never use these algorithms in production.
import java.security.KeyPairGenerator;
import java.security.MessageDigest;
import javax.crypto.Cipher;

public final class LegacyTokenCrypto {
    public static void demonstrate() throws Exception {
        MessageDigest.getInstance("MD5");
        Cipher.getInstance("DESede/CBC/PKCS5Padding");
        KeyPairGenerator rsa = KeyPairGenerator.getInstance("RSA");
        rsa.initialize(2048);
    }
}
