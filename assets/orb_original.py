#!/usr/bin/env python3
"""ARISE orb — 100% PySide6 / Qt-pure rendering.

User direction (2026-06-21): rebuild from scratch in PySide6 + Qt.
Stop embedding HTML/JS/Three.js inside QtWebEngine — the wireframe
sphere wasn't rendering reliably inside the embedded webview. This
version draws everything with QPainter on a custom QWidget. No
QWebEngineView, no Three.js, no canvas, no HTML.

Visual reference: the StartCo presentation orb (image #14 in the
session): radial dark-blue background, soft cyan glow halo, geodesic
wireframe sphere rotating in the center, scattered twinkling stars,
"ARISE" wordmark over the sphere, "VOICE MODE ACTIVE" status below.

Window: frameless + translucent + circular mask + always-on-top +
drag-from-anywhere + optional snap-to-terminal (Windows only).

Usage (called from launcher.go or `praxisgenai orb`):

    python orb_window.py <url> <width> <height> <x> <y>

The <url> arg is accepted but ignored — kept for backward
compatibility with the launcher signature. The orb no longer needs an
HTTP server to render; state updates come over SSE in a background
thread if a server URL is provided.

Dependencies:
    PySide6     (pip install PySide6)
    psutil      (optional, for snap detection on Windows)
    pywin32     (optional, Windows only — snap + window detection)
"""
import math
import os
import random
import sys
import threading
import time
from urllib.parse import urlparse


# ── Geometry: fibonacci sphere + nearest-neighbor edges ─────────────────────

def fibonacci_sphere(samples: int):
    """Return `samples` points roughly evenly distributed on a unit sphere
    via the golden-angle Fibonacci spiral. Cheaper than a real
    icosahedral subdivision and visually indistinguishable at this scale.
    """
    points = []
    phi = math.pi * (3.0 - math.sqrt(5.0))
    for i in range(samples):
        y = 1.0 - (i / max(samples - 1, 1)) * 2.0
        r = math.sqrt(max(0.0, 1.0 - y * y))
        theta = phi * i
        x = math.cos(theta) * r
        z = math.sin(theta) * r
        points.append((x, y, z))
    return points


def build_edges(points, k: int = 6):
    """For each point, connect it to its k nearest neighbors. Returns a
    set of (i, j) pairs with i < j so each edge is unique. k=6 gives
    the geodesic-mesh look StartCo's Three.js icosphere has.
    """
    edges = set()
    n = len(points)
    for i in range(n):
        xi, yi, zi = points[i]
        dists = []
        for j in range(n):
            if j == i:
                continue
            xj, yj, zj = points[j]
            dx = xi - xj
            dy = yi - yj
            dz = zi - zj
            dists.append((dx * dx + dy * dy + dz * dz, j))
        dists.sort()
        for _, j in dists[:k]:
            a, b = (i, j) if i < j else (j, i)
            edges.add((a, b))
    return list(edges)


# ── Terminal-window discovery (Windows) ─────────────────────────────────────

def find_terminal_hwnd():
    try:
        import win32gui
    except ImportError:
        return None

    user_name = os.environ.get("PRAXISGENAI_USER_NAME", "praxisgenai").lower()
    needles = [user_name, "praxisgenai", "🔷"]
    matches = []

    def cb(hwnd, _):
        try:
            if not win32gui.IsWindowVisible(hwnd):
                return True
            title = (win32gui.GetWindowText(hwnd) or "").lower()
            if not title or title.startswith("arise"):
                return True
            if any(n in title for n in needles):
                matches.append(hwnd)
        except Exception:
            pass
        return True

    try:
        win32gui.EnumWindows(cb, None)
    except Exception:
        matches = []

    if matches:
        terminal_classes = {"ConsoleWindowClass", "CASCADIA_HOSTING_WINDOW_CLASS"}
        for hwnd in matches:
            try:
                cls = win32gui.GetClassName(hwnd) or ""
                if cls in terminal_classes:
                    return hwnd
            except Exception:
                continue
        return matches[0]
    return None


def get_window_rect(hwnd):
    try:
        import win32gui
        if not win32gui.IsWindow(hwnd):
            return None
        return win32gui.GetWindowRect(hwnd)
    except Exception:
        return None


# ── SSE client (background thread) ──────────────────────────────────────────

def sse_loop(url, state_setter, stop_event):
    """Lightweight SSE reader. Connects to /events and parses
    `event: state` / `data: {json}` pairs, calling state_setter(dict)
    on each. Reconnects on failure. Runs until stop_event is set.
    """
    if not url:
        return
    base = url.rstrip("/")
    events_url = base + "/events"
    try:
        import urllib.request
    except ImportError:
        return

    import json
    while not stop_event.is_set():
        try:
            req = urllib.request.Request(events_url, headers={"Accept": "text/event-stream"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                event_name = None
                buf = []
                while not stop_event.is_set():
                    line = resp.readline()
                    if not line:
                        break
                    s = line.decode("utf-8", errors="ignore").rstrip("\r\n")
                    if s == "":
                        if event_name == "state" and buf:
                            try:
                                payload = json.loads("".join(buf))
                                state_setter(payload)
                            except Exception:
                                pass
                        event_name = None
                        buf = []
                        continue
                    if s.startswith("event:"):
                        event_name = s[6:].strip()
                    elif s.startswith("data:"):
                        buf.append(s[5:].strip())
        except Exception:
            pass
        stop_event.wait(1.0)


# ── Orb widget ──────────────────────────────────────────────────────────────

def build_app(url, width, height, x, y, snap_hwnd, snap_margin):
    from PySide6.QtCore import Qt, QTimer, QPointF, QRectF, QPoint, Signal
    from PySide6.QtGui import (
        QPainter, QColor, QPen, QBrush, QFont, QFontDatabase, QRadialGradient,
        QRegion, QPalette,
    )
    from PySide6.QtWidgets import QApplication, QWidget

    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    # Load JetBrains Mono Bold — same font StartCo's orb uses for the
    # ARISE wordmark. Bundled as a .ttf inside internal/orb/assets/.
    # If the file is missing or load fails, Qt falls back through its
    # substitution chain (we still ask for a monospaced font below).
    jetbrains_family = None
    here = os.path.dirname(os.path.abspath(__file__))
    ttf_path = os.path.join(here, "JetBrainsMono-Bold.ttf")
    if os.path.exists(ttf_path):
        font_id = QFontDatabase.addApplicationFont(ttf_path)
        if font_id != -1:
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                jetbrains_family = families[0]

    # Pre-compute the geometry once — the rotation matrix runs in
    # paintEvent, but the base point cloud and the edge list are static.
    SPHERE_POINTS = fibonacci_sphere(80)
    SPHERE_EDGES = build_edges(SPHERE_POINTS, k=6)

    # Per-speaker accent palette. The orb tints sphere edges, glow ring,
    # jupiter particles, sphere vertices and the ARISE wordmark halo
    # according to who currently owns the conversation. The wordmark
    # core stays near-white in all variants so "ARISE" reads cleanly.
    #
    # Keep the keys in sync with the SpeakerOrchestrator / SpeakerSubagent
    # / SpeakerHuman constants in internal/orb/controller.go.
    SPEAKER_PALETTE = {
        "orchestrator": {
            "accent":   (116, 246, 255),  # cyan — Jarvis default
            "particle": (170, 232, 255),
            "vertex":   (170, 245, 255),
            "core":     (210, 248, 255),
        },
        "subagent": {
            "accent":   (199, 146, 234),  # purple — delegated work
            "particle": (220, 180, 245),
            "vertex":   (224, 196, 250),
            "core":     (238, 222, 250),
        },
        "human": {
            "accent":   (255, 171, 102),  # orange — user is talking
            "particle": (255, 200, 145),
            "vertex":   (255, 210, 165),
            "core":     (255, 235, 215),
        },
    }

    for name, rgb in {"approval": (255, 192, 80), "error": (255, 100, 110), "working": (80, 150, 255)}.items():
        SPEAKER_PALETTE[name] = {"accent": rgb, "particle": rgb, "vertex": rgb, "core": (240, 245, 255)}

    class OrbWidget(QWidget):
        """Top-level frameless circular widget. Draws everything itself
        with QPainter — no children, no QWebEngineView, no HTML."""

        # Cross-thread signal: apply_state runs in the SSE reader thread,
        # but Qt widget operations (resize, setMask, …) must happen on
        # the main thread. Emitting this signal from the SSE thread
        # auto-queues the slot call on the widget's thread via Qt's
        # default queued-connection semantics.
        size_changed = Signal(int)
        visibility_changed = Signal(bool)

        def __init__(self):
            super().__init__()

            opaque = os.environ.get("PRAXISGENAI_ORB_OPAQUE", "").lower() in ("1", "true", "yes")
            framed = os.environ.get("PRAXISGENAI_ORB_FRAMED", "").lower() in ("1", "true", "yes")

            flags = Qt.WindowStaysOnTopHint
            if not framed:
                flags |= Qt.FramelessWindowHint
            self.setWindowFlags(flags)
            self.setWindowTitle("ARISE")
            self.setMouseTracking(True)

            if not opaque:
                self.setAttribute(Qt.WA_TranslucentBackground, True)
                pal = self.palette()
                pal.setColor(QPalette.Window, QColor(0, 0, 0, 0))
                self.setPalette(pal)

            self.resize(width, height)
            self.move(x, y)

            # Animation state.
            self.rotation = 0.0
            self.pulse = 0.0
            self.t0 = time.time()
            self.speaking = False
            self.listening = False
            self.status_label = "IDLE"
            # `speaker` drives the accent color via SPEAKER_PALETTE.
            # Unknown values fall back to orchestrator (cyan).
            self.speaker = "orchestrator"
            # speak_start captures the wall-clock moment self.speaking
            # flipped to True so the speech-amplitude oscillator below
            # has a stable t0 and the animation doesn't jerk between
            # frames. Reset to 0 when speaking stops.
            self.speak_start = 0.0

            # Ring particles — Jupiter-style orbital halo around the
            # sphere. Mirrors the StartCo fallback's _seedParticles:
            # 48 evenly-spaced points, modest radius variation,
            # individual phase offsets for shimmer.
            self.ring_particles = []
            self._seed_ring()

            self._drag_offset = None
            self._apply_round_mask()

            # Cross-thread resize + visibility hookups — see `size_changed`
            # declaration above. Qt routes these onto the widget's thread
            # automatically via queued connection.
            self.size_changed.connect(self._resize_to)
            self.visibility_changed.connect(self._set_visible)

            timer = QTimer(self)
            timer.timeout.connect(self._tick)
            timer.start(33)  # ~30fps

        # ── State updates from SSE ─────────────────────────────────────
        def apply_state(self, payload: dict):
            new_speaking = bool(payload.get("speaking"))
            # Rising edge detection: when TTS just started, snapshot
            # wall-clock so the speech-amplitude oscillator below has a
            # stable t0. Without this each frame would recompute the
            # phase against a stale start time and produce flicker.
            if new_speaking and not self.speaking:
                self.speak_start = time.time()
            self.speaking = new_speaking
            self.listening = bool(payload.get("listening"))
            spk = (payload.get("speaker") or "").strip().lower()
            self.speaker = spk if spk in SPEAKER_PALETTE else "orchestrator"
            # `reason` is the per-state label the Go side pushes ("wake",
            # "listening", "thinking", "speaking", "voice mode ending").
            # When set we prefer it — generic labels (LISTENING…, VOICE
            # MODE ACTIVE) hide the difference between wake-idle and
            # mid-utterance listening, which is exactly what the wake
            # mode needs to surface.
            reason = (payload.get("reason") or "").strip()
            if reason:
                self.status_label = reason.upper()
            elif self.speaking:
                self.status_label = "SPEAKING…"
            elif self.listening:
                self.status_label = "LISTENING…"
            else:
                self.status_label = "IDLE"
            # /changesize pushes a new square side here. Resize must run
            # on the Qt main thread — apply_state is invoked from the
            # SSE reader thread, so we emit a signal whose connected
            # slot is queued onto the widget's (main) thread by Qt.
            # Bounds match LoadPersistedSize to reject garbage payloads.
            try:
                size_px = int(payload.get("size") or 0)
            except (TypeError, ValueError):
                size_px = 0
            if 80 <= size_px <= 2000 and size_px != self.width():
                self.size_changed.emit(size_px)

            # /voice changes can ask the orb to hide (v2t / off) or show
            # again. `visible` is None in payloads that don't touch it.
            visible = payload.get("visible")
            if isinstance(visible, bool):
                self.visibility_changed.emit(visible)

        # ── Palette helpers — drive the per-speaker tint ───────────────
        def _palette(self):
            return SPEAKER_PALETTE.get(self.speaker, SPEAKER_PALETTE["orchestrator"])

        def accent(self, alpha: int):
            r, g, b = self._palette()["accent"]
            return QColor(r, g, b, max(0, min(255, alpha)))

        def particle_color(self, alpha: int):
            r, g, b = self._palette()["particle"]
            return QColor(r, g, b, max(0, min(255, alpha)))

        def vertex_color(self, alpha: int):
            r, g, b = self._palette()["vertex"]
            return QColor(r, g, b, max(0, min(255, alpha)))

        def core_color(self, alpha: int):
            r, g, b = self._palette()["core"]
            return QColor(r, g, b, max(0, min(255, alpha)))

        # ── Animation ──────────────────────────────────────────────────
        def _tick(self):
            self.rotation += 0.012
            self.pulse += 0.06
            self.update()

        # ── Ring particles ─────────────────────────────────────────────
        def _seed_ring(self):
            # 80 particles for a denser Jupiter-ring look — original
            # StartCo used 48, but with the smaller sphere the ring
            # reads thinner so we boost the count.
            n = 80
            self.ring_particles = []
            for i in range(n):
                self.ring_particles.append({
                    "angle": (math.pi * 2 * i) / n,
                    # Doubled the base + random component so the ring
                    # visibly spins instead of crawling.
                    "speed": 0.005 + random.random() * 0.009,
                    "radius_frac": 0.27 + random.random() * 0.16,
                    "size": 0.9 + random.random() * 2.2,
                    "offset": random.random() * math.pi * 2,
                })

        # ── Circular mask ──────────────────────────────────────────────
        def _apply_round_mask(self):
            side = min(self.width(), self.height())
            ox = (self.width() - side) // 2
            oy = (self.height() - side) // 2
            self.setMask(QRegion(ox, oy, side, side, QRegion.Ellipse))

        def resizeEvent(self, event):
            super().resizeEvent(event)
            self._apply_round_mask()
            # Ring uses fractional radii — no re-seed needed on resize.

        # ── Live resize from /changesize ───────────────────────────────
        # Called on the Qt main thread (via QTimer.singleShot from
        # apply_state). Keeps the orb centered around its current top-
        # left so the user doesn't see it jump across the screen — the
        # snap timer will pull it back to the terminal edge on the next
        # tick if snap is on.
        def _resize_to(self, px: int):
            self.resize(px, px)
            self._apply_round_mask()

        # ── Hide / show from /voice mode changes ───────────────────────
        def _set_visible(self, visible: bool):
            if visible:
                self.show()
            else:
                self.hide()

        # ── Drag from anywhere ─────────────────────────────────────────
        def mousePressEvent(self, event):
            if event.button() == Qt.LeftButton:
                self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()

        def mouseMoveEvent(self, event):
            if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
                self.move(event.globalPosition().toPoint() - self._drag_offset)
                event.accept()

        def mouseReleaseEvent(self, event):
            self._drag_offset = None
            event.accept()

        # ── Paint ──────────────────────────────────────────────────────
        def paintEvent(self, event):
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing, True)
            w, h = self.width(), self.height()
            cx, cy = w / 2.0, h / 2.0
            short_side = min(w, h)

            # ── Backdrop: radial dark-blue gradient ─────────────────
            bg = QRadialGradient(cx, cy, short_side * 0.55)
            bg.setColorAt(0.0, QColor(22, 56, 96, 235))
            bg.setColorAt(0.55, QColor(8, 22, 42, 220))
            bg.setColorAt(1.0, QColor(0, 4, 12, 210))
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(bg))
            p.drawEllipse(QPointF(cx, cy), short_side / 2 - 1, short_side / 2 - 1)

            # ── Subtle grid lines (faint dotted ring pattern, tinted) ──
            p.setPen(QPen(self.accent(14), 1, Qt.DotLine))
            for r in range(int(short_side * 0.18), int(short_side * 0.5), 28):
                p.drawEllipse(QPointF(cx, cy), r, r)

            # ── Speech-amplitude oscillator ─────────────────────────
            # When ARISE is speaking, the glow/sphere should LOOK like
            # speech — not a uniform sine wave. We stack four oscillators
            # at irrational ratios so the pattern never repeats and
            # reads as "talking":
            #   drift     ~1.7 Hz  → breath / sentence cadence
            #   syllables ~5.3 Hz  → word-rate beat (Spanish ~5 syl/s)
            #   jitter    ~13 Hz   → consonant attacks
            #   bursts    exponential decay every 1/4 s → phoneme onsets
            #
            # Reference: StartCo presentation orb's TTS reactive
            # animation (see Michael/NOTES.md). The real envelope path
            # (synthesize audio first, extract RMS per 50 ms) is in the
            # backlog — engram topic orb/tts-amplitude-animation —
            # this is the "80 % of the visual without new deps" path.
            if self.speaking and self.speak_start > 0:
                t = time.time() - self.speak_start
                drift     = 0.20 * math.sin(t * 1.7)
                syllables = 0.30 * math.sin(t * 5.3 + 0.7)
                jitter    = 0.10 * math.sin(t * 13.1 + 1.3)
                burst     = 0.25 * math.exp(-((t * 4.0) % 1.0) * 3.0)
                pulse_amp = 0.45 + drift + syllables + jitter + burst
                if pulse_amp < 0.20:
                    pulse_amp = 0.20
                elif pulse_amp > 1.20:
                    pulse_amp = 1.20
            elif self.listening:
                # Gentler oscillation while listening — same idea but
                # narrower amplitude range so the listening state is
                # visibly calmer than speaking.
                t = time.time() - self.t0
                pulse_amp = 0.5 + 0.5 * math.sin(self.pulse * 0.4)
                pulse_amp = pulse_amp * 1.3 + 0.2
            else:
                # Idle baseline — slow uniform breathing.
                pulse_amp = 0.5 + 0.5 * math.sin(self.pulse * 0.4)
            for layer in range(6):
                t = layer / 5.0
                amp_factor = 1.0 if not (self.speaking or self.listening) else 1.6
                rr = short_side * (0.38 + 0.04 * pulse_amp * amp_factor - 0.03 * t)
                base_alpha = 28
                if self.speaking:
                    base_alpha = 60
                elif self.listening:
                    base_alpha = 42
                alpha = int(base_alpha * (1.0 - t) * (0.65 + 0.35 * pulse_amp))
                if alpha <= 0:
                    continue
                p.setPen(QPen(self.accent(alpha), 1.8, Qt.SolidLine))
                p.setBrush(Qt.NoBrush)
                p.drawEllipse(QPointF(cx, cy), rr, rr)

            # ── Jupiter-style orbital ring of particles ─────────────
            # The original StartCo fallback flattens Y by 0.7 to fake a
            # tilted orbital plane — same trick here. Particles orbit
            # around the sphere at varying radii, twinkling via their
            # individual `offset` phases.
            now = (time.time() - self.t0)
            for particle in self.ring_particles:
                angle = particle["angle"] + now * particle["speed"] * 60  # match JS feel
                radius = short_side * particle["radius_frac"] + math.sin(now * 1.5 + particle["offset"]) * 4
                dx = math.cos(angle) * radius
                dy = math.sin(angle) * radius * 0.32  # flattened — ring of Jupiter perspective
                px = cx + dx
                py = cy + dy
                # Particles in the back half (sin(angle) < 0 after the
                # flatten) are dimmer so the ring reads as a 3D loop
                # around the sphere instead of a flat halo.
                back = math.sin(angle) < 0
                alpha_base = 110 if back else 220
                shimmer = 0.55 + 0.45 * math.sin(now * 2.3 + particle["offset"])
                alpha = int(alpha_base * shimmer)
                size_px = particle["size"] * (0.7 if back else 1.0)
                p.setPen(Qt.NoPen)
                p.setBrush(self.particle_color(alpha))
                p.drawEllipse(QPointF(px, py), size_px, size_px)

            # ── Wireframe sphere — scales with the speech oscillator ─
            # When speaking, the sphere radius tracks pulse_amp so the
            # body of the orb literally pulses with the simulated speech
            # rhythm above (not just the glow ring). Idle / listening
            # stay on the slow sine for a calmer baseline.
            if self.speaking:
                # pulse_amp ∈ [0.20, 1.20] → scale ∈ [0.93, 1.15]
                breathe_scale = 1.0 + 0.20 * (pulse_amp - 0.45)
            elif self.listening:
                breathe_phase = math.sin(self.pulse * 0.4)
                breathe_scale = 1.0 + 0.06 * breathe_phase
            else:
                breathe_phase = math.sin(self.pulse * 0.4)
                breathe_scale = 1.0 + 0.02 * breathe_phase
            sphere_r = short_side * 0.17 * breathe_scale
            cos_r = math.cos(self.rotation)
            sin_r = math.sin(self.rotation)
            # Slight tilt on X so the equator isn't a flat line.
            tilt = math.radians(18)
            cos_t = math.cos(tilt)
            sin_t = math.sin(tilt)

            projected = []
            for (px, py, pz) in SPHERE_POINTS:
                # Rotate around Y axis (rotation), then tilt around X.
                rx = px * cos_r - pz * sin_r
                rz0 = px * sin_r + pz * cos_r
                ry = py * cos_t - rz0 * sin_t
                rz = py * sin_t + rz0 * cos_t
                sx = cx + rx * sphere_r
                sy = cy + ry * sphere_r
                depth = (rz + 1.0) * 0.5  # 0=back, 1=front
                projected.append((sx, sy, depth))

            # Edges
            for i, j in SPHERE_EDGES:
                p1 = projected[i]
                p2 = projected[j]
                avg = (p1[2] + p2[2]) * 0.5
                alpha = int(45 + 175 * avg)
                width_px = 0.6 + 0.9 * avg
                p.setPen(QPen(self.accent(alpha), width_px))
                p.drawLine(QPointF(p1[0], p1[1]), QPointF(p2[0], p2[1]))

            # Vertices (brighter on the front face)
            for (sx, sy, depth) in projected:
                alpha = int(120 + 135 * depth)
                radius_px = 0.9 + 1.4 * depth
                p.setPen(Qt.NoPen)
                p.setBrush(self.vertex_color(alpha))
                p.drawEllipse(QPointF(sx, sy), radius_px, radius_px)

            # ── ARISE wordmark, centered ────────────────────────────
            # JetBrains Mono Bold — same font StartCo uses for ARISE.
            # Loaded from the bundled .ttf in build_app(); falls back
            # to Consolas (Windows monospace) → generic monospace.
            arise_size = max(8, int(short_side * 0.048))
            family = jetbrains_family or "Consolas"
            font = QFont(family, arise_size)
            font.setStyleHint(QFont.Monospace)
            font.setBold(True)
            font.setLetterSpacing(QFont.AbsoluteSpacing, max(3.0, short_side * 0.018))
            p.setFont(font)
            # Glow halo by drawing the text multiple times in the accent
            # before the bright per-speaker core (almost-white but warm
            # for human, cool for cyan/purple).
            p.setPen(self.accent(110))
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1)]:
                p.drawText(self.rect().adjusted(dx, dy, dx, dy), Qt.AlignCenter, "ARISE")
            p.setPen(self.core_color(250))
            p.drawText(self.rect(), Qt.AlignCenter, "ARISE")

            # ── Status line at the bottom ───────────────────────────
            font_status = QFont("Segoe UI", max(7, int(short_side * 0.028)))
            font_status.setBold(True)
            font_status.setLetterSpacing(QFont.AbsoluteSpacing, 1.8)
            p.setFont(font_status)
            status_color = self.accent(220) if (self.speaking or self.listening) else QColor(150, 180, 210, 170)
            p.setPen(status_color)
            bullet = "●" if (self.speaking or self.listening) else "○"
            p.drawText(
                QRectF(0, h - short_side * 0.10, w, short_side * 0.08),
                Qt.AlignCenter,
                f"{bullet}  {self.status_label}",
            )

    window = OrbWidget()
    window.show()

    # ── SSE state subscription ──────────────────────────────────────
    stop_event = threading.Event()
    if url:
        # Use the URL passed in by the launcher (http://127.0.0.1:PORT/).
        parsed = urlparse(url)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            base = f"{parsed.scheme}://{parsed.netloc}"
            t = threading.Thread(
                target=sse_loop,
                args=(base, window.apply_state, stop_event),
                daemon=True,
            )
            t.start()

    # ── Snap to terminal ────────────────────────────────────────────
    if snap_hwnd is not None:
        state = {"last_term_pos": None}

        def tick_snap():
            rect = get_window_rect(snap_hwnd)
            if rect is None:
                window.close()
                return
            left, top, right, _ = rect
            term_pos = (right, top)
            if term_pos != state["last_term_pos"]:
                target_x = right - window.width() - snap_margin
                target_y = top + snap_margin
                window.move(QPoint(target_x, target_y))
                state["last_term_pos"] = term_pos

        snap_timer = QTimer(window)
        snap_timer.timeout.connect(tick_snap)
        snap_timer.start(100)

    return app, window


def main() -> int:
    try:
        from PySide6.QtWidgets import QApplication  # noqa: F401
    except ImportError:
        print("orb_window: PySide6 not installed — run `pip install PySide6`", file=sys.stderr)
        return 2

    if len(sys.argv) < 6:
        print("orb_window: usage: orb_window.py <url> <width> <height> <x> <y>", file=sys.stderr)
        return 3

    url = sys.argv[1]
    try:
        width = int(sys.argv[2])
        height = int(sys.argv[3])
        x = int(sys.argv[4])
        y = int(sys.argv[5])
    except ValueError as err:
        print(f"orb_window: numeric arg parse failed: {err}", file=sys.stderr)
        return 4

    snap = os.environ.get("PRAXISGENAI_ORB_SNAP", "1").lower() not in ("0", "false", "no", "off")
    snap_hwnd = find_terminal_hwnd() if snap else None
    try:
        snap_margin = int(os.environ.get("PRAXISGENAI_ORB_SNAP_MARGIN", "8"))
    except ValueError:
        snap_margin = 8

    app, _window = build_app(url, width, height, x, y, snap_hwnd, snap_margin)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

