package com.praxis.arise;

/** No permission or process restart can silently re-enable listening. */
final class WakeState {
    enum Panel { HIDDEN, COMPACT, EXPANDED }
    boolean listening;
    Panel panel = Panel.HIDDEN;
    boolean start(boolean microphone, boolean overlay, boolean notifications, boolean configured) {
        if (!microphone || !overlay || !notifications || !configured) return false;
        listening = true;
        return true;
    }
    boolean detected(boolean unlocked) {
        if (!listening || !unlocked || panel != Panel.HIDDEN) return false;
        panel = Panel.COMPACT;
        return true;
    }
    void hide() { panel = Panel.HIDDEN; }
    void expand() { if (panel != Panel.HIDDEN) panel = Panel.EXPANDED; }
    void stop() { listening = false; hide(); }
}
