# -*- coding: utf-8 -*-
"""
แถบเพลงลอย (Media Bar) สำหรับ Kuroya Window Manager
====================================================
เลียนแบบจอควบคุมมีเดียของ Windows 11: รูปปก + ชื่อเพลง/ศิลปิน/ช่อง,
แถบเวลา (คลิกเพื่อเลื่อน), ปุ่ม ⏮ ⏸/▶ ⏭ — ลากย้ายได้ ซ่อนได้ (Ctrl+Alt+M)

ทำงานผ่าน Windows SMTC (System Media Transport Controls) เหมือนจอที่ป๊อป
เหนือนาฬิกาของ Windows 11 จึงรู้เพลงที่กำลังเล่นจาก Chrome/Edge (YouTube),
Spotify, Media Player ฯลฯ โดยอัตโนมัติ

ต้องติดตั้งเพิ่มเฉพาะถ้าจะใช้แถบเพลง (โปรแกรมหลักไม่ต้อง):
    pip install winsdk Pillow
ถ้า Python เวอร์ชันใหม่เกินที่ winsdk รองรับ ให้ใช้ชุด winrt แทน:
    pip install winrt-runtime winrt-Windows.Media.Control winrt-Windows.Storage.Streams Pillow
ถ้าไม่ติดตั้ง โปรแกรมหลักยังใช้ได้ปกติ — แค่แถบเพลงจะปิดอยู่

โมดูลนี้ import ได้บนทุก OS (ตรวจหา dependencies แล้วรายงานผ่าน AVAILABLE)
"""
from __future__ import annotations

import asyncio
import datetime
import io
import math
import queue
import threading
import time

try:
    import tkinter as tk
except ImportError:
    tk = None

# ---------- WinRT backend: รองรับทั้งแพ็กเกจ winsdk และชุด winrt-* ----------
_MEDIA_MGR = None
_BACKEND = None
DataReader = None
try:
    from winsdk.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as _MEDIA_MGR,
    )
    from winsdk.windows.storage.streams import DataReader
    _BACKEND = "winsdk"
except Exception:
    try:
        from winrt.windows.media.control import (
            GlobalSystemMediaTransportControlsSessionManager as _MEDIA_MGR,
        )
        from winrt.windows.storage.streams import DataReader
        _BACKEND = "winrt"
    except Exception:
        _MEDIA_MGR = None
        _BACKEND = None

try:
    from PIL import Image, ImageDraw
    PIL_OK = True
except ImportError:
    PIL_OK = False

AVAILABLE = (_MEDIA_MGR is not None) and (DataReader is not None) and (tk is not None)

# ---------- ธีมสี (เข้าชุดกับโปรแกรมหลัก) ----------
MAGIC = "#010203"          # สีโปร่งใส (transparentcolor)
PANEL_BG = "#141518"       # พื้นแผงเข้มแบบ Windows 11
PANEL_BORDER = "#2e3138"
FG = "#f2f3f5"
MUTED = "#9aa0a6"
TRACK = "#3a3d44"
FILL = "#ffffff"
BTN_BG = "#2a2d33"
BTN_BORDER = "#3d414a"
NOTE_BG = "#23252b"

THUMB_SIZE = 56


def _font(size=10, bold=False):
    return ("Leelawadee UI", size, "bold" if bold else "normal")


def _glyph(size=12):
    return ("Segoe UI Symbol", size)


# ---------------------------------------------------------------------------
# ฟังก์ชันช่วย (pure functions — ทดสอบข้ามแพลตฟอร์มได้)
# ---------------------------------------------------------------------------

def fmt_time(sec):
    """วินาที -> 'm:ss' เช่น 83 -> '1:23'"""
    try:
        sec = max(0, int(round(float(sec))))
    except Exception:
        sec = 0
    return f"{sec // 60}:{sec % 60:02d}"


def fmt_remaining(sec):
    """เวลาที่เหลือ -> '-m:ss' เช่น 91 -> '-1:31'"""
    return "-" + fmt_time(sec)


def compute_elapsed(snap, now_mono):
    """เวลาเล่นปัจจุบัน: ต่อยอดจากตอน sample ล่าสุดด้วย playback rate แล้ว clamp ที่ความยาวเพลง"""
    pos = float(snap.get("pos_s") or 0.0)
    dur = float(snap.get("dur_s") or 0.0)
    if snap.get("playing"):
        rate = float(snap.get("rate") or 0.0)
        pos += (float(now_mono) - float(snap.get("updated_mono") or now_mono)) * rate
    pos = max(0.0, pos)
    if dur > 0:
        pos = min(pos, dur)
    return pos


def pretty_app_id(aumid):
    """AUMID เช่น 'Chrome_ChromeTvl' -> 'Google Chrome' (ใช้แสดงว่าเพลงมาจากแอปไหน)"""
    if not aumid:
        return ""
    token = aumid.split("!")[0].split("\\")[-1].split("/")[-1]
    token = token.split("_")[0]
    if token.lower().endswith(".exe"):
        token = token[:-4]
    low = token.lower()
    if low.startswith("spotify"):
        return "Spotify"
    mapping = {
        "chrome": "Google Chrome", "msedge": "Microsoft Edge",
        "firefox": "Firefox", "brave": "Brave", "opera": "Opera",
        "vivaldi": "Vivaldi", "itunes": "iTunes",
        "microsoft.windowsmediaplayer": "Media Player",
        "applicationframehost": "แอป Windows",
    }
    if low in mapping:
        return mapping[low]
    return token


def thumb_png(raw, size=THUMB_SIZE, radius=10):
    """แปลงไบต์รูปจาก SMTC เป็น PNG จัตุรัสมุมโค้ง (ใช้ Pillow ถ้ามี; ไม่มีคืนของเดิม)"""
    if not raw:
        return None
    if PIL_OK:
        try:
            im = Image.open(io.BytesIO(raw)).convert("RGBA")
            w, h = im.size
            s = min(w, h)
            im = im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))
            im = im.resize((size, size), Image.LANCZOS)
            mask = Image.new("L", (size, size), 0)
            d = ImageDraw.Draw(mask)
            d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
            im.putalpha(mask)
            out = io.BytesIO()
            im.save(out, "PNG")
            return out.getvalue()
        except Exception:
            return raw
    return raw


EMPTY_SNAP = {
    "available": False, "title": "", "artist": "", "app": "",
    "status": "", "playing": False, "rate": 0.0,
    "pos_s": 0.0, "dur_s": 0.0, "updated_mono": 0.0,
    "thumb_png": None, "thumb_key": "",
}


# ---------------------------------------------------------------------------
# เธรดอ่านสถานะมีเดียจาก Windows SMTC (WinRT)
# ---------------------------------------------------------------------------

class SMTCWatcher(threading.Thread):
    """โพลสถานะเพลงจาก Windows ทุก ~0.8 วิ + รับคำสั่ง play/pause/next/prev/seek"""

    POLL = 0.8

    def __init__(self):
        super().__init__(daemon=True, name="kuroya-media")
        self._lock = threading.Lock()
        self._snap = dict(EMPTY_SNAP)
        self._q = queue.Queue()
        self._stop_evt = threading.Event()
        self._mgr = None
        self._props_key = None
        self._thumb_png = None

    # ---- ฝั่ง UI thread ----
    def snapshot(self):
        with self._lock:
            return dict(self._snap)

    def command(self, name, arg=None):
        self._q.put((name, arg))

    def stop(self):
        self._stop_evt.set()

    # ---- ฝั่ง watcher thread ----
    def run(self):
        if not AVAILABLE:
            return
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._main())
        except Exception:
            pass
        finally:
            try:
                loop.close()
            except Exception:
                pass

    async def _main(self):
        try:
            mgr = await _MEDIA_MGR.request_async()
        except Exception:
            with self._lock:
                self._snap = dict(EMPTY_SNAP)
            return
        self._mgr = mgr
        while not self._stop_evt.is_set():
            await self._drain()
            await self._sample()
            wake = time.monotonic() + self.POLL
            while not self._stop_evt.is_set() and time.monotonic() < wake:
                if not self._q.empty():
                    break
                await asyncio.sleep(0.1)

    async def _drain(self):
        """คำสั่งจาก UI thread (play/pause/next/prev/seek) — ทำทันทีที่หยิบได้"""
        while True:
            try:
                name, arg = self._q.get_nowait()
            except queue.Empty:
                return
            try:
                await self._exec(name, arg)
            except Exception:
                pass
            try:
                await self._sample()   # สถานะเปลี่ยนแล้ว อัปเดต snapshot ทันที
            except Exception:
                pass

    async def _exec(self, name, arg):
        mgr = self._mgr
        if mgr is None:
            return
        try:
            sess = mgr.get_current_session()
        except Exception:
            return
        if sess is None:
            return
        if name == "play":
            await sess.try_play_async()
        elif name == "pause":
            await sess.try_pause_async()
        elif name == "next":
            await sess.try_skip_next_async()
        elif name == "prev":
            await sess.try_skip_previous_async()
        elif name == "seek":
            secs = max(0.0, float(arg))
            await sess.try_change_timeline_position_async(datetime.timedelta(seconds=secs))

    async def _sample(self):
        now = time.monotonic()
        mgr = self._mgr
        if mgr is None:
            return
        try:
            sess = mgr.get_current_session()
        except Exception:
            sess = None
        if sess is None:
            with self._lock:
                self._snap = dict(EMPTY_SNAP, available=True, updated_mono=now)
            self._props_key = None
            self._thumb_png = None
            return
        try:
            pb = sess.get_playback_info()
            tl = sess.get_timeline_properties()
            props = await sess.try_get_media_properties_async()
        except Exception:
            return

        status_name = getattr(pb.status, "name", "") or str(pb.status)
        status_key = status_name.split(".")[-1].strip().lower()
        playing = status_key == "playing"
        try:
            rate = float(pb.playback_rate or 0.0)
        except Exception:
            rate = 0.0
        if not playing:
            rate = 0.0
        try:
            pos = float(tl.position.total_seconds())
        except Exception:
            pos = 0.0
        try:
            dur = float(tl.end_time.total_seconds())
        except Exception:
            dur = 0.0
        aumid = ""
        try:
            aumid = sess.source_app_user_model_id or ""
        except Exception:
            pass
        title = props.title or ""
        artist = props.artist or props.subtitle or ""
        app = pretty_app_id(aumid)

        key = (aumid, title, artist)
        thumb = self._thumb_png
        if key != self._props_key:
            self._props_key = key
            raw = await self._read_thumb(props)
            thumb = thumb_png(raw)
            self._thumb_png = thumb
        thumb_key = f"{aumid}|{title}|{artist}"
        snap = {
            "available": True, "title": title, "artist": artist, "app": app,
            "status": status_key, "playing": playing, "rate": rate,
            "pos_s": pos, "dur_s": dur, "updated_mono": now,
            "thumb_png": thumb, "thumb_key": thumb_key,
        }
        with self._lock:
            self._snap = snap

    async def _read_thumb(self, props):
        ref = getattr(props, "thumbnail", None)
        if ref is None or DataReader is None:
            return None
        try:
            stream = await ref.open_read_async()
            size = int(stream.size)
            if size <= 0:
                return None
            reader = DataReader(stream)
            n = await reader.load_async(size)
            data = bytes(reader.read_bytes(int(n)))
            return data
        except Exception:
            return None


# ---------------------------------------------------------------------------
# หน้าต่างแถบเพลง (tkinter canvas มุมโค้งด้วย transparentcolor)
# ---------------------------------------------------------------------------

class MediaBar:
    W, H = 396, 152
    R = 18
    TRACK_X0, TRACK_X1 = 24, W - 24
    TRACK_Y0, TRACK_Y1 = 92, 98
    CTRL_Y = 132
    BUTTON_TAGS = ("btn_play", "btn_next", "btn_prev", "btn_seek", "btn_menu")

    def __init__(self, root, settings, persist_cb=None):
        self.root = root
        self.settings = settings
        self.persist_cb = persist_cb
        self.watcher = SMTCWatcher()
        self.watcher.start()
        self._photo = None
        self._photo_key = None
        self._snap = dict(EMPTY_SNAP)
        self._user_hidden = False     # ผู้ใช้สั่งซ่อนเอง — ไม่ auto-show อีกในเซสชันนี้
        self._user_opened = False     # เปิดเอง (เผื่อไม่มีเพลง อย่า auto-hide)
        self._empty_since = None
        self._topmost = True
        self._drag = None

        win = tk.Toplevel(root)
        win.title("KuroyaWM-Media")   # ขึ้นต้น KuroyaWM เพื่อให้โปรแกรมหลักกรองออก
        win.overrideredirect(True)
        win.configure(bg=MAGIC)
        try:
            win.attributes("-transparentcolor", MAGIC)
        except Exception:
            pass
        win.attributes("-topmost", True)
        self.win = win
        self.canvas = tk.Canvas(win, width=self.W, height=self.H, bg=MAGIC,
                                highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self._build_menu()
        self._place()
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._motion)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.canvas.bind("<Button-3>", self._open_menu)
        self._tick()

    # ---------- ตำแหน่ง / การมองเห็น ----------
    def _place(self):
        x = self.settings.get("media_x")
        y = self.settings.get("media_y")
        if not isinstance(x, int) or not isinstance(y, int):
            try:
                sw = self.root.winfo_screenwidth()
            except Exception:
                sw = 1920
            x = max(0, sw // 2 - self.W // 2)   # กลางจอด้านบน เหมือนภาพตัวอย่าง
            y = 8
        self.win.geometry(f"{self.W}x{self.H}+{int(x)}+{int(y)}")

    def is_visible(self):
        try:
            return self.win.state() == "normal"
        except Exception:
            return False

    def show(self):
        self.win.deiconify()
        self.win.lift()
        try:
            self.win.attributes("-topmost", self._topmost)
        except Exception:
            pass

    def hide(self, user=False):
        self.win.withdraw()
        if user:
            self._user_hidden = True
            self._user_opened = False

    def toggle(self):
        if self.is_visible():
            self.hide(user=True)
        else:
            self._user_opened = True
            self.show()

    def close(self):
        try:
            self.watcher.stop()
        except Exception:
            pass
        try:
            self.win.destroy()
        except Exception:
            pass

    # ---------- ลูปวาดภาพ ----------
    def _tick(self):
        try:
            snap = self.watcher.snapshot()
            self._snap = snap
            has_media = bool(snap.get("title"))
            if (has_media and self.settings.get("media_on", True)
                    and not self._user_hidden and not self.is_visible()):
                self.show()
            if self.is_visible() and not has_media and not self._user_opened:
                # ไม่มีสื่อเล่นนานเกิน 8 วิ และเปิดมาโดยอัตโนมัติ — ซ่อนเอง
                if self._empty_since is None:
                    self._empty_since = time.monotonic()
                elif time.monotonic() - self._empty_since > 8:
                    self.hide(user=False)
            elif has_media:
                self._empty_since = None
            self._draw(snap)
        except Exception:
            pass
        try:
            self.root.after(250, self._tick)
        except Exception:
            pass

    # ---------- วาด ----------
    def _rounded_points(self, x0, y0, x1, y1, r, seg=6):
        if r <= 0 or (x1 - x0) < 2 * r or (y1 - y0) < 2 * r:
            return [x0, y0, x1, y0, x1, y1, x0, y1]
        pts = []

        def arc(cx, cy, a0, a1):
            for i in range(seg + 1):
                a = math.radians(a0 + (a1 - a0) * i / seg)
                pts.append(cx + r * math.cos(a))
                pts.append(cy + r * math.sin(a))

        arc(x1 - r, y0 + r, -90, 0)
        arc(x1 - r, y1 - r, 0, 90)
        arc(x0 + r, y1 - r, 90, 180)
        arc(x0 + r, y0 + r, 180, 270)
        return pts

    def _rrect(self, x0, y0, x1, y1, r, fill, outline="", width=0, tags=()):
        pts = self._rounded_points(x0, y0, x1, y1, r)
        return self.canvas.create_polygon(*pts, fill=fill, outline=outline,
                                          width=width, tags=tags, smooth=False)

    def _clip(self, text, limit):
        if len(text) <= limit:
            return text
        return text[: limit - 1] + "…"

    def _draw(self, snap):
        c = self.canvas
        c.delete("all")
        has = bool(snap.get("title"))
        playing = bool(snap.get("playing"))
        muted = MUTED if has else "#6b7078"

        # พื้นแผงมุมโค้ง
        self._rrect(2, 2, self.W - 3, self.H - 3, self.R,
                    PANEL_BG, PANEL_BORDER, 1, tags=("drag",))

        # รูปปก (หรือกล่องโน้ตเพลงถ้าไม่มีรูป)
        if self._photo is None or snap.get("thumb_key") != self._photo_key:
            png = snap.get("thumb_png")
            if png:
                try:
                    self._photo = tk.PhotoImage(data=png, master=self.win)
                    self._photo_key = snap.get("thumb_key")
                except Exception:
                    self._photo = None
                    self._photo_key = ""
            else:
                self._photo = None
                self._photo_key = ""
        if self._photo is not None:
            c.create_image(46, 42, image=self._photo, tags=("drag",))
        else:
            self._rrect(18, 14, 74, 70, 12, NOTE_BG, tags=("drag",))
            c.create_text(46, 41, text="♪", fill=muted, font=_glyph(18), tags=("drag",))

        # ชื่อเพลง / ศิลปิน·แอป
        if has:
            title = self._clip(snap.get("title", ""), 30)
            artist = self._clip((snap.get("artist") or "").strip(), 28)
            app = (snap.get("app") or "").strip()
            sub = artist if not app else (f"{artist} · {app}" if artist else app)
        else:
            title = "ไม่มีเพลงที่กำลังเล่น"
            sub = "เปิดเพลงใน Chrome/Edge/Spotify แล้วขึ้นเองที่นี่"
        c.create_text(86, 26, anchor="w", text=title, fill=FG,
                      font=_font(11, True), tags=("drag",))
        c.create_text(86, 50, anchor="w", text=self._clip(sub, 40), fill=MUTED,
                      font=_font(9), tags=("drag",))
        c.create_text(self.W - 22, 26, text="⋮", fill=MUTED, font=_glyph(12),
                      tags=("btn_menu",))

        # แถบเวลา
        elapsed = compute_elapsed(snap, time.monotonic())
        dur = float(snap.get("dur_s") or 0.0)
        self._rrect(self.TRACK_X0, self.TRACK_Y0, self.TRACK_X1, self.TRACK_Y1, 3,
                    TRACK, tags=("btn_seek", "drag"))
        if dur > 0:
            frac = max(0.0, min(1.0, elapsed / dur))
            fx = self.TRACK_X0 + frac * (self.TRACK_X1 - self.TRACK_X0)
            if fx > self.TRACK_X0 + 2:
                self._rrect(self.TRACK_X0, self.TRACK_Y0, fx, self.TRACK_Y1, 3,
                            FILL, tags=("btn_seek",))
        c.create_text(self.TRACK_X0, 110, anchor="w", text=fmt_time(elapsed),
                      fill=MUTED, font=_font(8))
        if dur > 0:
            c.create_text(self.TRACK_X1, 110, anchor="e",
                          text=fmt_remaining(dur - elapsed), fill=MUTED, font=_font(8))

        # ปุ่มควบคุม
        cx = self.W // 2
        y = self.CTRL_Y
        # เล่น/พัก (วงกลมใหญ่)
        c.create_oval(cx - 17, y - 17, cx + 17, y + 17, fill=BTN_BG,
                      outline=BTN_BORDER, tags=("btn_play",))
        c.create_text(cx, y - 1, text=("⏸" if playing else "▶"),
                      fill=FG if has else muted, font=_glyph(13), tags=("btn_play",))
        # เพลงก่อนหน้า / ถัดไป (+ พื้นที่คลิกใหญ่)
        c.create_rectangle(cx - 84, y - 18, cx - 44, y + 18, fill="", outline="",
                           tags=("btn_prev",))
        c.create_text(cx - 64, y, text="⏮", fill=FG if has else muted,
                      font=_glyph(13), tags=("btn_prev",))
        c.create_rectangle(cx + 44, y - 18, cx + 84, y + 18, fill="", outline="",
                           tags=("btn_next",))
        c.create_text(cx + 64, y, text="⏭", fill=FG if has else muted,
                      font=_glyph(13), tags=("btn_next",))

    # ---------- อินพุต ----------
    def _tag_at(self, x, y):
        found = set()
        try:
            for iid in self.canvas.find_overlapping(x - 2, y - 2, x + 2, y + 2):
                found.update(self.canvas.gettags(iid))
        except Exception:
            return None
        for pref in self.BUTTON_TAGS:
            if pref in found:
                return pref
        return None

    def _press(self, e):
        self._drag = {"x": e.x_root, "y": e.y_root,
                      "wx": self.win.winfo_x(), "wy": self.win.winfo_y(),
                      "tag": self._tag_at(e.x, e.y), "moved": False}

    def _motion(self, e):
        if not self._drag:
            return
        dx = e.x_root - self._drag["x"]
        dy = e.y_root - self._drag["y"]
        if abs(dx) + abs(dy) > 6:
            self._drag["moved"] = True
        if self._drag["moved"]:
            self.win.geometry(f"+{self._drag['wx'] + dx}+{self._drag['wy'] + dy}")

    def _release(self, e):
        d = self._drag
        self._drag = None
        if not d:
            return
        if d["moved"]:
            if self.persist_cb:
                try:
                    self.persist_cb({"media_x": int(self.win.winfo_x()),
                                     "media_y": int(self.win.winfo_y())})
                except Exception:
                    pass
            return
        tag = d["tag"]
        if tag == "btn_play":
            playing = bool(self._snap.get("playing"))
            self.watcher.command("pause" if playing else "play")
        elif tag == "btn_next":
            self.watcher.command("next")
        elif tag == "btn_prev":
            self.watcher.command("prev")
        elif tag == "btn_seek":
            dur = float(self._snap.get("dur_s") or 0.0)
            if dur > 0:
                frac = (e.x - self.TRACK_X0) / float(self.TRACK_X1 - self.TRACK_X0)
                self.watcher.command("seek", min(max(frac, 0.0), 1.0) * dur)
        elif tag == "btn_menu":
            self._open_menu_at(self.win.winfo_pointerx(), self.win.winfo_pointery())

    def _open_menu(self, e):
        self._open_menu_at(e.x_root, e.y_root)

    # ---------- เมนูคลิกขวา ----------
    def _build_menu(self):
        self._topmost_var = tk.BooleanVar(value=True)
        m = tk.Menu(self.win, tearoff=0, bg=PANEL_BG, fg=FG,
                    font=_font(9), activebackground=BTN_BG, bd=0)
        m.add_command(label="เล่น/พัก", command=lambda: self.watcher.command(
            "pause" if self._snap.get("playing") else "play"))
        m.add_command(label="เพลงถัดไป", command=lambda: self.watcher.command("next"))
        m.add_command(label="เพลงก่อนหน้า", command=lambda: self.watcher.command("prev"))
        m.add_separator()
        m.add_checkbutton(label="อยู่บนสุดเสมอ", variable=self._topmost_var,
                          command=self._apply_topmost)
        m.add_command(label="ซ่อนแถบนี้ (Ctrl+Alt+M)", command=lambda: self.hide(user=True))
        self.menu = m

    def _open_menu_at(self, x, y):
        try:
            self._topmost_var.set(self._topmost)
            self.menu.tk_popup(x, y)
        finally:
            self.menu.grab_release()

    def _apply_topmost(self):
        self._topmost = bool(self._topmost_var.get())
        try:
            self.win.attributes("-topmost", self._topmost)
        except Exception:
            pass


def create_media_bar(root, settings, persist_cb=None):
    """สร้างแถบเพลง (เริ่ม watcher ให้ด้วย) — เรียกเฉพาะเมื่อ AVAILABLE เป็น True"""
    return MediaBar(root, settings, persist_cb)
