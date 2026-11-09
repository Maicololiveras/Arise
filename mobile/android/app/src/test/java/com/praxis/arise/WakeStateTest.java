package com.praxis.arise;
import org.junit.Test;
import static org.junit.Assert.*;
public class WakeStateTest {
    @Test public void requiresEachPermissionAndModel() {
        for(int missing=0;missing<4;missing++) { boolean[] p={true,true,true,true};p[missing]=false;WakeState s=new WakeState();assertFalse(s.start(p[0],p[1],p[2],p[3]));assertFalse(s.detected(true)); }
    }
    @Test public void wakeExpandHideAndStopAreDifferent() {
        WakeState s=new WakeState();assertTrue(s.start(true,true,true,true));assertTrue(s.detected(true));assertFalse(s.detected(true));
        assertEquals(WakeState.Panel.COMPACT,s.panel);s.expand();assertEquals(WakeState.Panel.EXPANDED,s.panel);
        s.hide();assertTrue(s.listening);assertTrue(s.detected(true));s.stop();assertFalse(s.listening);assertFalse(s.detected(true));
    }
    @Test public void neverShowsHistoryOverLockScreen() {
        WakeState s=new WakeState();s.start(true,true,true,true);assertFalse(s.detected(false));assertEquals(WakeState.Panel.HIDDEN,s.panel);
    }
    @Test public void recreationDoesNotRestoreListening() { assertFalse(new WakeState().listening); }
    @Test public void originRejectsEscapesAndAllowsOnlyConfiguredHost() {
        assertEquals("https://pc.tail.ts.net",Origin.validate("https://pc.tail.ts.net/"));
        for(String bad:new String[]{"http://pc.tail.ts.net","https://evil.test","https://pc.ts.net@evil.test","https://pc.ts.net:443","https://pc.ts.net/path","https://pc.ts.net?q=x","https://pc.ts.net#x"}) {
            try { Origin.validate(bad); fail(bad); } catch(IllegalArgumentException expected) {}
        }
        assertTrue(Origin.allows("https://pc.tail.ts.net","https://pc.tail.ts.net/messages"));
        assertFalse(Origin.allows("https://pc.tail.ts.net","https://other.tail.ts.net/"));
        assertFalse(Origin.allows("https://pc.tail.ts.net","https://user@pc.tail.ts.net/"));
        assertFalse(Origin.allows("https://pc.tail.ts.net","file:///etc/passwd"));
    }
}
