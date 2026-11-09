package com.praxis.arise;
import org.junit.Test;
import static org.junit.Assert.*;
public class AppUpdateTest {
    private static final String VERSION=BuildConfig.IS_PREVIEW ? "0.1.1-qa" : "0.1.1";
    private static final String URL="https://github.com/Maicololiveras/Arise/releases/download/"+AppUpdate.PREFIX+VERSION+"/"+AppUpdate.APK;
    @Test public void validQaVersion() {
        AppUpdate u=new AppUpdate(1,BuildConfig.APPLICATION_ID,AppUpdate.CHANNEL,2,VERSION,URL);
        assertEquals(2,u.code);assertEquals(URL,u.url);
    }
    @Test public void rejectsForeignOrMalformedUpdates() {
        for(String url:new String[]{"http://evil.test/a.apk",URL+"?token=x",URL.replace("Maicololiveras","other"),URL.replace(VERSION,"0.0.0")}) {
            try { new AppUpdate(1,BuildConfig.APPLICATION_ID,AppUpdate.CHANNEL,2,VERSION,url);fail(); }
            catch(IllegalArgumentException expected) {}
        }
        try { new AppUpdate(1,BuildConfig.APPLICATION_ID,"wrong-channel",2,VERSION,URL);fail(); }
        catch(IllegalArgumentException expected) {}
    }
}
