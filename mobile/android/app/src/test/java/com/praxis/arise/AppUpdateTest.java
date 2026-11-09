package com.praxis.arise;
import org.junit.Test;
import static org.junit.Assert.*;
public class AppUpdateTest {
    private static final String URL="https://github.com/Maicololiveras/Arise/releases/download/android-qa-v0.1.1-qa/ARISE-Android-QA.apk";
    @Test public void validQaVersion() {
        AppUpdate u=new AppUpdate(1,"com.praxis.arise.qa","qa",2,"0.1.1-qa",URL);
        assertEquals(2,u.code);assertEquals(URL,u.url);
    }
    @Test public void rejectsForeignOrMalformedUpdates() {
        for(String url:new String[]{"http://evil.test/a.apk",URL+"?token=x",URL.replace("Maicololiveras","other"),URL.replace("0.1.1-qa","0.1.0-qa")}) {
            try { new AppUpdate(1,"com.praxis.arise.qa","qa",2,"0.1.1-qa",url);fail(); }
            catch(IllegalArgumentException expected) {}
        }
        try { new AppUpdate(1,"com.praxis.arise.qa","main",2,"0.1.1-qa",URL);fail(); }
        catch(IllegalArgumentException expected) {}
    }
}
