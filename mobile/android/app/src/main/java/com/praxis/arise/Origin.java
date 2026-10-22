package com.praxis.arise;
import java.net.URI;

final class Origin {
    static String validate(String value) {
        URI u = URI.create(value.trim());
        String host = u.getHost();
        if (!"https".equals(u.getScheme()) || host == null || !host.endsWith(".ts.net")
                || host.length() <= 7 || u.getRawUserInfo() != null || u.getPort() != -1
                || u.getRawQuery() != null || u.getRawFragment() != null
                || !(u.getRawPath().isEmpty() || "/".equals(u.getRawPath())))
            throw new IllegalArgumentException("Usa el origen HTTPS de Tailscale, sin ruta ni puerto.");
        return "https://" + host;
    }
    static boolean allows(String origin, String url) {
        try {
            URI u = URI.create(url);
            return origin.equals(u.getScheme() + "://" + u.getHost()) && u.getPort() == -1 && u.getRawUserInfo() == null;
        } catch (RuntimeException e) { return false; }
    }
}
