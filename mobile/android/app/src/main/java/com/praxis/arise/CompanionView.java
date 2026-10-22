package com.praxis.arise;
import android.content.Context;
import android.webkit.*;
import android.net.http.SslError;
import java.io.ByteArrayInputStream;

/** Shares the existing scoped HttpOnly cookie, never a privileged native JS bridge. */
final class CompanionView {
    static WebView create(Context context, String origin) {
        WebView view = new WebView(context);
        WebSettings settings = view.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setAllowFileAccess(false); settings.setAllowContentAccess(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setMediaPlaybackRequiresUserGesture(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(view, false);
        view.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) {
                return !Origin.allows(origin, r.getUrl().toString());
            }
            @Override public WebResourceResponse shouldInterceptRequest(WebView v, WebResourceRequest r) {
                if (Origin.allows(origin, r.getUrl().toString())) return null;
                return new WebResourceResponse("text/plain", "UTF-8", new ByteArrayInputStream(new byte[0]));
            }
            @Override public void onReceivedSslError(WebView v, SslErrorHandler handler, SslError error) { handler.cancel(); }
        });
        view.setWebChromeClient(new WebChromeClient() {
            @Override public void onPermissionRequest(PermissionRequest request) { request.deny(); }
        });
        view.loadUrl(origin + "/");
        return view;
    }
}
