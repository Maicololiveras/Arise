package com.praxis.arise;

import java.io.*;
import java.net.URL;
import javax.net.ssl.HttpsURLConnection;
import org.json.JSONObject;

/** Public QA metadata only; never sends companion credentials or pairing tokens. */
final class AppUpdate {
    static final String FEED="https://github.com/Maicololiveras/Arise/releases/download/android-qa/ARISE-Android-update.json";
    final int code;
    final String version, url;
    AppUpdate(int schema, String app, String channel, int code, String version, String url) {
        if(schema!=1 || !"com.praxis.arise.qa".equals(app) || !"qa".equals(channel)
            || code<1 || version==null || !version.matches("[0-9]+\\.[0-9]+\\.[0-9]+-qa")
            || !("https://github.com/Maicololiveras/Arise/releases/download/android-qa-v"+version+"/ARISE-Android-QA.apk").equals(url))
            throw new IllegalArgumentException("Invalid Android QA metadata");
        this.code=code; this.version=version; this.url=url;
    }
    static AppUpdate fetch() throws Exception {
        HttpsURLConnection connection=(HttpsURLConnection)new URL(FEED).openConnection();
        connection.setConnectTimeout(5000);connection.setReadTimeout(5000);
        connection.setRequestProperty("User-Agent","ARISE-Android-QA-update");
        try {
            if(connection.getResponseCode()!=200) throw new IOException("Update metadata unavailable");
            try(InputStream input=connection.getInputStream();ByteArrayOutputStream output=new ByteArrayOutputStream()) {
                byte[] buffer=new byte[1024];int n;
                while((n=input.read(buffer))!=-1) {
                    if(output.size()+n>16384) throw new IOException("Oversized metadata");
                    output.write(buffer,0,n);
                }
                JSONObject json=new JSONObject(output.toString("UTF-8"));
                return new AppUpdate(json.getInt("schema"),json.getString("applicationId"),json.getString("channel"),json.getInt("versionCode"),json.getString("versionName"),json.getString("apkUrl"));
            }
        } finally { connection.disconnect(); }
    }
}
