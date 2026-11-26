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
import ctypes
import datetime
import io
import math
import os
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

AUDIO_EMPTY = {"available": False, "playing": [], "max_peak": 0.0, "volume": None}


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
        self._chosen_aumid = ""

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

    @staticmethod
    def _iter_sessions(mgr):
        """ทุกเซสชันสื่อที่ Windows รู้จัก (Chrome, Edge, Spotify, Media Player ฯลฯ)
        รองรับหลายรูปแบบ API กันไว้เมื่อ projection ต่างกันตามเวอร์ชันแพ็กเกจ"""
        try:
            vv = mgr.get_sessions()
        except Exception:
            return []
        out = []
        try:
            for s in vv:                      # IVectorView ทำ iterable ได้บางเวอร์ชัน
                out.append(s)
                if len(out) >= 16:
                    return out
            if out:
                return out
        except Exception:
            out = []
        try:
            try:
                n = int(vv.size)
            except Exception:
                n = int(vv.size())
            for i in range(min(max(n, 0), 16)):
                out.append(vv.get_at(i))
        except Exception:
            pass
        return out

    @staticmethod
    def _aumid_of(sess):
        try:
            return sess.source_app_user_model_id or ""
        except Exception:
            return ""

    @staticmethod
    def _is_playing(sess):
        try:
            pb = sess.get_playback_info()
            nm = getattr(pb.status, "name", "") or str(pb.status)
            return nm.split(".")[-1].strip().lower() == "playing"
        except Exception:
            return False

    def _best_session(self, mgr):
        """เลือกเซสชันที่จะแสดง/ควบคุม: ตัวที่กำลังเล่นมาก่อนเสมอ (ครอบคลุม
        เปิด Chrome ค้างไว้แต่กำลังฟัง Spotify), ถ้าไม่มีใครเล่นเอาตัวเดิมที่จำไว้
        (sticky), ถ้าไม่มีเลยเอาตัวแรก; fallback เป็น get_current_session"""
        items = self._iter_sessions(mgr)
        if not items:
            try:
                s = mgr.get_current_session()
                if s:
                    self._chosen_aumid = self._aumid_of(s)
                return s
            except Exception:
                return None
        playing = [s for s in items if self._is_playing(s)]
        if playing:
            self._chosen_aumid = self._aumid_of(playing[0])
            return playing[0]
        chosen = self._chosen_aumid
        for s in items:
            if chosen and self._aumid_of(s) == chosen:
                return s                   # คงตัวเดิมไว้ (จะได้ไม่กระโดดเปลี่ยนเอง)
        self._chosen_aumid = self._aumid_of(items[0])
        return items[0]

    async def _exec(self, name, arg):
        mgr = self._mgr
        if mgr is None:
            return
        sess = self._best_session(mgr)
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
        sess = self._best_session(mgr)
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
# ตรวจจับเสียงจริงระดับโปรเซสด้วย WASAPI (ครอบคลุมแท็บ/คลิปที่ไม่รายงานชื่อเพลง)
# หลักการ: ถาม Windows ว่าโปรเซสไหนกำลังส่งเสียงออกลำโพง (peak meter ต่อ session)
# ใช้ ctypes เรียก COM ตรง ๆ — ไม่ต้องติดตั้งไลบรารีเพิ่ม
# ---------------------------------------------------------------------------

CLSID_MMDeviceEnumerator = "BCDE0395-E52F-467C-8E3D-C4579291692E"
IID_IAudioSessionManager2 = "77AA99A0-1BD6-484F-8BC7-2C654C9A9B6F"
IID_IAudioSessionEnumerator = "E2F5BB11-0570-40CA-ACDD-3AA01277DEE8"
IID_IAudioMeterInformation = "C02216F6-5C67-4BCC-9F21-3A909B770AD0"
IID_IAudioSessionControl2 = "BFB7FF88-7239-4FC9-8FA2-07C950BE9C64"
IID_IAudioEndpointVolume = "5CDF2C82-841E-4546-9722-0CF74078229A"

CLSCTX_ALL = 23
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_MEDIA_NEXT_TRACK = 0xB6
VK_MEDIA_PREV_TRACK = 0xB5

FRIENDLY_PROCESS = {
    "chrome": "Google Chrome", "msedge": "Microsoft Edge", "firefox": "Firefox",
    "brave": "Brave", "opera": "Opera", "vivaldi": "Vivaldi",
    "spotify": "Spotify", "discord": "Discord", "steamwebhelper": "Steam",
    "obs64": "OBS Studio", "obs32": "OBS Studio", "wmplayer": "Media Player",
    "vlc": "VLC", "itunes": "iTunes", "potplayer": "PotPlayer",
    "applicationframehost": "แอป Windows", "ytmusic": "YouTube Music",
}


def friendly_process_name(exe):
    """ชื่อไฟล์โปรเซส -> ชื่อที่คนอ่านรู้เรื่อง เช่น chrome.exe -> Google Chrome"""
    base = (exe or "").split("/")[-1].split("\\")[-1]
    if base.lower().endswith(".exe"):
        base = base[:-4]
    return FRIENDLY_PROCESS.get(base.lower(), base or "โปรแกรม")


def merge_modes(smtc_title, audio_playing_count):
    """เลือกโหมดแสดงผล: มีข้อมูลเพลงจาก SMTC > มีเสียงเล่นจริง > ไม่มีอะไร"""
    if smtc_title:
        return "media"
    if audio_playing_count > 0:
        return "audio"
    return "none"


def send_media_key(vk):
    """กดปุ่มสื่อของ Windows (Play/Pause/Next/Prev) — OS ส่งต่อให้แท็บ/แอปที่เล่นอยู่"""
    if os.name != "nt":
        return
    try:
        u32 = ctypes.WinDLL("user32")
        u32.keybd_event(vk, 0, 0, 0)
        u32.keybd_event(vk, 0, 2, 0)   # KEYEVENTF_KEYUP
    except Exception:
        pass


class _ComError(Exception):
    pass


class _GUID(ctypes.Structure):
    _fields_ = [("d1", ctypes.c_uint32), ("d2", ctypes.c_uint16),
                ("d3", ctypes.c_uint16), ("d4", ctypes.c_ubyte * 8)]


def _guid(text):
    b = bytes.fromhex(text.replace("-", ""))
    g = _GUID()
    g.d1 = int.from_bytes(b[0:4], "little")
    g.d2 = int.from_bytes(b[4:6], "little")
    g.d3 = int.from_bytes(b[6:8], "little")
    g.d4 = (ctypes.c_ubyte * 8)(*b[8:16])
    return g


def _com_fn(ptr, index, restype, *argtypes):
    """หยิบฟังก์ชันลำดับที่ index จาก vtable ของ COM object (this = ptr)"""
    vtbl_addr = ctypes.cast(ptr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents.value
    fn_addr = ctypes.cast(vtbl_addr, ctypes.POINTER(ctypes.c_void_p))[index]
    proto = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)
    return proto(fn_addr)


def _com_release(ptr):
    try:
        if ptr:
            _com_fn(ptr, 2, ctypes.c_ulong)(ptr)   # IUnknown::Release
    except Exception:
        pass


def _com_check(hr, what):
    if hr & 0x80000000:
        raise _ComError(f"{what} hr=0x{hr & 0xFFFFFFFF:08X}")


def process_exe_name(pid):
    """ชื่อ .exe ของ pid (ค้นผ่าน OpenProcess + QueryFullProcessImageNameW)"""
    if os.name != "nt" or not pid:
        return ""
    try:
        k32 = ctypes.WinDLL("kernel32")
        h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
        if not h:
            return ""
        try:
            size = ctypes.c_uint(1024)
            buf = ctypes.create_unicode_buffer(1024)
            if k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                return buf.value
            return ""
        finally:
            k32.CloseHandle(h)
    except Exception:
        return ""


class AudioWatcher(threading.Thread):
    """โพล peak meter ของทุก audio session ทุก ~0.5 วิ — รายงานว่าโปรเซสไหนกำลังมีเสียง
    เสียงต้องดังต่อเนื่องเกิน SUSTAIN วินาทีถึงจะนับเป็น 'กำลังเล่น' (กันเสียงสั้น ๆ รบกวน)"""

    POLL = 0.5
    LOUD = 0.02        # เกณฑ์ความดังขั้นต่ำ (peak 0-1)
    SUSTAIN = 1.5      # วินาทีที่ต้องมีเสียงต่อเนื่อง

    def __init__(self):
        super().__init__(daemon=True, name="kuroya-audio")
        self._lock = threading.Lock()
        self._snap = {"available": False, "playing": [], "max_peak": 0.0,
                      "volume": None}
        self._stop_evt = threading.Event()
        self._q = queue.Queue()
        self._ole32 = None
        self._stack = None      # (enum, dev, mgr, epvol) COM pointers ที่ใช้ซ้ำ
        self._last = {}         # pid -> (mono, peak)
        self._since = {}        # pid -> mono เริ่มมีเสียงต่อเนื่อง
        self._names = {}        # pid -> ชื่อ exe (แคช)
        self._errs = 0

    def snapshot(self):
        with self._lock:
            return {"available": self._snap["available"],
                    "playing": list(self._snap["playing"]),
                    "max_peak": self._snap["max_peak"],
                    "volume": self._snap["volume"]}

    def command(self, name, arg=None):
        """คำสั่งจาก UI เช่น set_volume 0..1 (ปรับความดังหลักของเครื่อง)"""
        self._q.put((name, arg))

    def stop(self):
        self._stop_evt.set()

    # ---- เธรดหลัก ----
    def run(self):
        if os.name != "nt":
            return
        try:
            self._ole32 = ctypes.WinDLL("ole32")
            self._ole32.CoInitializeEx(None, 0x0)   # COINIT_MULTITHREADED
        except Exception:
            return
        try:
            self._build_stack()
            while not self._stop_evt.is_set():
                t0 = time.monotonic()
                self._drain()
                apps = None
                volume = None
                try:
                    apps = self._poll_sessions()
                    volume = self._read_master_volume()
                    self._errs = 0
                except Exception:
                    self._errs += 1
                    if self._errs >= 4:
                        self._build_stack()   # อุปกรณ์/ลำโพงเปลี่ยน — สร้างใหม่
                self._update(apps, volume)
                dt = time.monotonic() - t0
                self._stop_evt.wait(max(0.05, self.POLL - dt))
        finally:
            self._teardown()
            try:
                self._ole32.CoUninitialize()
            except Exception:
                pass

    def _drain(self):
        """คำสั่งจาก UI (ตอนนี้มี set_volume — ปรับความดังหลักทั้งเครื่อง)"""
        while True:
            try:
                name, arg = self._q.get_nowait()
            except queue.Empty:
                return
            try:
                if name == "set_volume" and self._stack and self._stack[3]:
                    v = max(0.0, min(1.0, float(arg)))
                    _com_fn(self._stack[3], 7, ctypes.c_long,
                            ctypes.c_float, ctypes.c_void_p)(
                        self._stack[3], v, None)   # IAudioEndpointVolume::SetMasterVolumeLevelScalar
            except Exception:
                pass

    def _read_master_volume(self):
        """ความดังหลักของเครื่อง 0..1 (คืน None ถ้าอ่านไม่ได้)"""
        if not self._stack or not self._stack[3]:
            return None
        try:
            v = ctypes.c_float(0.0)
            hr = _com_fn(self._stack[3], 9, ctypes.c_long,
                         ctypes.POINTER(ctypes.c_float))(
                self._stack[3], ctypes.byref(v))   # GetMasterVolumeLevelScalar
            if hr & 0x80000000:
                return None
            return max(0.0, min(1.0, float(v.value)))
        except Exception:
            return None

    # ---- COM plumbing ----
    def _build_stack(self):
        old = self._stack
        self._stack = None
        if old:
            for p in old:
                _com_release(p)
        ole = self._ole32
        clsid = _guid(CLSID_MMDeviceEnumerator)
        enum = ctypes.c_void_p()
        hr = ole.CoCreateInstance(ctypes.byref(clsid), None, CLSCTX_ALL,
                                  ctypes.byref(clsid), ctypes.byref(enum))
        _com_check(hr, "CoCreateInstance")
        dev = ctypes.c_void_p()
        mgr = ctypes.c_void_p()
        try:
            _com_check(_com_fn(enum, 4, ctypes.c_long,
                               ctypes.c_int, ctypes.c_int,
                               ctypes.POINTER(ctypes.c_void_p))(
                enum, 0, 1, ctypes.byref(dev)), "GetDefaultAudioEndpoint")
            iid = _guid(IID_IAudioSessionManager2)
            _com_check(_com_fn(dev, 3, ctypes.c_long,
                               ctypes.POINTER(_GUID), ctypes.c_uint,
                               ctypes.c_void_p,
                               ctypes.POINTER(ctypes.c_void_p))(
                dev, ctypes.byref(iid), CLSCTX_ALL, None,
                ctypes.byref(mgr)), "Activate(session mgr)")
            epvol = ctypes.c_void_p()
            iidv = _guid(IID_IAudioEndpointVolume)
            hr = _com_fn(dev, 3, ctypes.c_long,
                         ctypes.POINTER(_GUID), ctypes.c_uint,
                         ctypes.c_void_p,
                         ctypes.POINTER(ctypes.c_void_p))(
                dev, ctypes.byref(iidv), CLSCTX_ALL, None, ctypes.byref(epvol))
            if hr & 0x80000000:
                epvol = None               # อ่าน/ปรับความดังไม่ได้ แต่มิเตอร์ยังใช้ได้
            self._stack = (enum, dev, mgr, epvol)
        except Exception:
            for p in (enum, dev, mgr):
                _com_release(p)
            raise

    def _teardown(self):
        if self._stack:
            for p in self._stack:
                _com_release(p)
            self._stack = None

    def _poll_sessions(self):
        """คืนรายการ (pid, peak) ของทุก session ที่มีระดับเสียง > 0"""
        if not self._stack:
            raise _ComError("no stack")
        enum_local = ctypes.c_void_p()
        _com_check(_com_fn(self._stack[2], 5, ctypes.c_long,
                           ctypes.POINTER(ctypes.c_void_p))(
            self._stack[2], ctypes.byref(enum_local)), "GetSessionEnumerator")
        try:
            n = ctypes.c_int(0)
            _com_check(_com_fn(enum_local, 3, ctypes.c_long,
                               ctypes.POINTER(ctypes.c_int))(
                enum_local, ctypes.byref(n)), "GetCount")
            out = []
            qi_iid_meter = _guid(IID_IAudioMeterInformation)
            qi_iid_c2 = _guid(IID_IAudioSessionControl2)
            for i in range(min(max(n.value, 0), 64)):
                ctrl = ctypes.c_void_p()
                try:
                    hr = _com_fn(enum_local, 4, ctypes.c_long,
                                 ctypes.c_int,
                                 ctypes.POINTER(ctypes.c_void_p))(
                        enum_local, i, ctypes.byref(ctrl))
                    if hr & 0x80000000 or not ctrl:
                        continue
                    peak = 0.0
                    pid = 0
                    meter = ctypes.c_void_p()
                    c2 = ctypes.c_void_p()
                    try:
                        qi = _com_fn(ctrl, 0, ctypes.c_long,
                                     ctypes.POINTER(_GUID),
                                     ctypes.POINTER(ctypes.c_void_p))
                        if qi(ctrl, ctypes.byref(qi_iid_meter),
                              ctypes.byref(meter)) >= 0 and meter:
                            v = ctypes.c_float(0.0)
                            if _com_fn(meter, 3, ctypes.c_long,
                                       ctypes.POINTER(ctypes.c_float))(
                                    meter, ctypes.byref(v)) >= 0:
                                peak = float(v.value)
                        if qi(ctrl, ctypes.byref(qi_iid_c2),
                              ctypes.byref(c2)) >= 0 and c2:
                            p = ctypes.c_uint32(0)
                            if _com_fn(c2, 12, ctypes.c_long,
                                       ctypes.POINTER(ctypes.c_uint32))(
                                    c2, ctypes.byref(p)) >= 0:
                                pid = int(p.value)
                    finally:
                        _com_release(meter)
                        _com_release(c2)
                    if peak > 0.001 and pid:
                        out.append((pid, peak))
                finally:
                    _com_release(ctrl)
            return out
        finally:
            _com_release(enum_local)

    # ---- ประมวลผล "เสียงต่อเนื่อง" ----
    def _update(self, apps, volume=None):
        now = time.monotonic()
        if apps is None:
            apps = []
        cur = {}
        for pid, peak in apps:
            if peak >= self.LOUD:
                cur[pid] = peak
                self._since.setdefault(pid, now)
            self._last[pid] = (now, peak)
        for pid in list(self._since):
            if pid not in cur:
                t, _pk = self._last.get(pid, (0.0, 0.0))
                if now - t > 1.0:      # เงียบไปแล้ว 1 วิ — นับว่าหยุด
                    del self._since[pid]
        for pid in list(self._last):
            if now - self._last[pid][0] > 6.0:
                del self._last[pid]
        playing = []
        for pid, peak in cur.items():
            if now - self._since[pid] >= self.SUSTAIN:
                if pid not in self._names:
                    self._names[pid] = friendly_process_name(process_exe_name(pid))
                playing.append({"pid": pid, "peak": peak,
                                "name": self._names.get(pid, "โปรแกรม")})
        playing.sort(key=lambda a: -a["peak"])
        with self._lock:
            self._snap = {"available": True, "playing": playing[:4],
                          "max_peak": max((p["peak"] for p in playing), default=0.0),
                          "volume": volume}


# ---------------------------------------------------------------------------
# หน้าต่างแถบเพลง (tkinter canvas มุมโค้งด้วย transparentcolor)
# ---------------------------------------------------------------------------

class MediaBar:
    W, H = 396, 152
    R = 18
    TRACK_X0, TRACK_X1 = 24, W - 24
    TRACK_Y0, TRACK_Y1 = 92, 98
    VOL_Y0, VOL_Y1 = 104, 112
    VOL_X1 = TRACK_X0 + 296
    CTRL_Y = 132
    BUTTON_TAGS = ("btn_play", "btn_next", "btn_prev", "btn_seek", "btn_menu",
                   "btn_vol")

    def __init__(self, root, settings, persist_cb=None):
        self.root = root
        self.settings = settings
        self.persist_cb = persist_cb
        self.watcher = SMTCWatcher()
        self.watcher.start()
        self.audio = AudioWatcher()
        self.audio.start()
        self._mode = "none"          # "media" | "audio" | "none"
        self._aud = {"available": False, "playing": [], "max_peak": 0.0}
        self._level = 0.0            # มิเตอร์เสียงแบบ smoothing
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
            if self.audio:
                self.audio.stop()
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
            self._aud = self.audio.snapshot() if self.audio else AUDIO_EMPTY
            has_media = bool(snap.get("title"))
            audio_playing = bool(self._aud.get("playing"))
            self._mode = merge_modes(snap.get("title"), len(self._aud.get("playing") or []))
            # มิเตอร์เสียง: เลื่อนแบบนุ่มเข้าหาค่า peak จริง
            target = float(self._aud.get("max_peak") or 0.0)
            self._level += (target - self._level) * 0.35
            if (self._mode != "none" and self.settings.get("media_on", True)
                    and not self._user_hidden and not self.is_visible()):
                self.show()
            if self.is_visible() and self._mode == "none" and not self._user_opened:
                # ไม่มีทั้งเพลงและเสียงนานเกิน 8 วิ และแถบเปิดมาโดยอัตโนมัติ — ซ่อนเอง
                if self._empty_since is None:
                    self._empty_since = time.monotonic()
                elif time.monotonic() - self._empty_since > 8:
                    self.hide(user=False)
            elif self._mode != "none":
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

        # ไม่มีชื่อเพลงแต่มีเสียงเล่นจริง (แท็บ/คลิปที่ไม่รายงาน SMTC) — การ์ดมิเตอร์เสียง
        if self._mode == "audio" and not has:
            self._draw_audio_card(c)
            return

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

    def _draw_audio_card(self, c):
        """การ์ดโหมด 'มีเสียงแต่ไม่รู้ชื่อเพลง' — โชว์มิเตอร์ที่ซิงค์กับเสียงจริง"""
        apps = self._aud.get("playing") or []
        name = apps[0]["name"] if apps else "โปรแกรม"
        c = self.canvas
        # พื้นแผง
        self._rrect(2, 2, self.W - 3, self.H - 3, self.R,
                    PANEL_BG, PANEL_BORDER, 1, tags=("drag",))
        # กล่องโน้ตเพลง + ขีดเสียงเต้นรอบ ๆ
        self._rrect(18, 14, 74, 70, 12, NOTE_BG, tags=("drag",))
        bars = max(1, min(5, int(round(self._level * 10 + 1))))
        for i in range(bars):
            bh = 6 + (i % 3) * 5
            c.create_rectangle(30 + i * 8, 58 - bh, 34 + i * 8, 58,
                               fill="#7b61ff" if i < bars - 1 else "#a68cff",
                               width=0, tags=("drag",))
        c.create_text(40, 30, text="♪", fill=FG, font=_glyph(16), tags=("drag",))

        # ชื่อแอปที่กำลังส่งเสียง
        n = len(apps)
        if n > 1:
            title = f"กำลังเล่นเสียง: {name} + อีก {n - 1}"
        else:
            title = f"กำลังเล่นเสียง: {name}"
        c.create_text(86, 26, anchor="w", text=self._clip(title, 30), fill=FG,
                      font=_font(11, True), tags=("drag",))
        c.create_text(86, 50, anchor="w",
                      text="แท็บ/คลิปที่ไม่รายงานชื่อเพลง • ปุ่มล่างควบคุมผ่าน Windows",
                      fill=MUTED, font=_font(8), tags=("drag",))
        c.create_text(self.W - 22, 26, text="⋮", fill=MUTED, font=_glyph(12),
                      tags=("btn_menu",))

        # แถบมิเตอร์เสียง (ซิงค์กับเสียงจริงแบบเรียลไทม์)
        lvl = max(0.0, min(1.0, self._level * 1.5))
        self._rrect(self.TRACK_X0, self.TRACK_Y0, self.TRACK_X1, self.TRACK_Y1, 3,
                    TRACK, tags=("drag",))
        fx = self.TRACK_X0 + lvl * (self.TRACK_X1 - self.TRACK_X0)
        if fx > self.TRACK_X0 + 2:
            self._rrect(self.TRACK_X0, self.TRACK_Y0, fx, self.TRACK_Y1, 3,
                        "#7b61ff", tags=("drag",))
        c.create_text(self.TRACK_X1 - 6, (self.TRACK_Y0 + self.TRACK_Y1) // 2,
                      anchor="e", text=f"เสียง {int(round(lvl * 100))}%",
                      fill="#ffffff" if lvl > 0.12 else MUTED, font=_font(8),
                      tags=("drag",))

        # แถบปรับความดังหลักของเครื่อง (master volume) — คลิก/ลากเพื่อปรับได้จริง
        vol = self._aud.get("volume") if isinstance(self._aud, dict) else None
        if vol is not None:
            vol = max(0.0, min(1.0, float(vol)))
            self._rrect(self.TRACK_X0, self.VOL_Y0, self.VOL_X1, self.VOL_Y1, 4,
                        TRACK, tags=("btn_vol",))
            fxv = self.TRACK_X0 + vol * (self.VOL_X1 - self.TRACK_X0)
            if fxv > self.TRACK_X0 + 2:
                self._rrect(self.TRACK_X0, self.VOL_Y0, fxv, self.VOL_Y1, 4,
                            FILL, tags=("btn_vol",))
            c.create_text(self.VOL_X1 + 8, (self.VOL_Y0 + self.VOL_Y1) // 2,
                          anchor="w", text=f"หมุนเสียงหลัก {int(round(vol * 100))}%",
                          fill=MUTED, font=_font(8), tags=("drag",))

        # ปุ่มควบคุม (ส่ง media key ให้ Windows — OS ส่งต่อให้แท็บที่เล่นอยู่)
        cx = self.W // 2
        y = self.CTRL_Y
        c.create_oval(cx - 17, y - 17, cx + 17, y + 17, fill=BTN_BG,
                      outline=BTN_BORDER, tags=("btn_play",))
        c.create_text(cx, y - 1, text="▶", fill=FG, font=_glyph(13),
                      tags=("btn_play",))
        c.create_rectangle(cx - 84, y - 18, cx - 44, y + 18, fill="", outline="",
                           tags=("btn_prev",))
        c.create_text(cx - 64, y, text="⏮", fill=FG, font=_glyph(13),
                      tags=("btn_prev",))
        c.create_rectangle(cx + 44, y - 18, cx + 84, y + 18, fill="", outline="",
                           tags=("btn_next",))
        c.create_text(cx + 64, y, text="⏭", fill=FG, font=_glyph(13),
                      tags=("btn_next",))

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

    def _set_volume_from_x(self, x):
        if not self.audio:
            return
        frac = (x - self.TRACK_X0) / float(self.VOL_X1 - self.TRACK_X0)
        self.audio.command("set_volume", min(max(frac, 0.0), 1.0))

    def _motion(self, e):
        if not self._drag:
            return
        dx = e.x_root - self._drag["x"]
        dy = e.y_root - self._drag["y"]
        if abs(dx) + abs(dy) > 6:
            self._drag["moved"] = True
        if self._drag["tag"] == "btn_vol":
            # ลากบนแถบความดัง = ปรับ master volume ต่อเนื่อง (ไม่ย้ายหน้าต่าง)
            if self._drag["moved"]:
                now = time.monotonic()
                if now - self._drag.get("last_set", 0.0) > 0.05:
                    self._drag["last_set"] = now
                    self._set_volume_from_x(e.x)
            return
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
        if tag == "btn_vol":
            if not d["moved"]:
                self._set_volume_from_x(e.x)      # คลิกจุดไหน เสียงไปจุดนั้นเลย
            else:
                self._set_volume_from_x(e.x)      # ปล่อยหลังลาก — ตั้งค่าสุดท้าย
            return
        if self._mode == "audio" and not self._snap.get("title"):
            # โหมดมิเตอร์เสียง: ส่ง media key ของ Windows ให้แท็บ/แอปที่กำลังเล่น
            if tag == "btn_play":
                send_media_key(VK_MEDIA_PLAY_PAUSE)
            elif tag == "btn_next":
                send_media_key(VK_MEDIA_NEXT_TRACK)
            elif tag == "btn_prev":
                send_media_key(VK_MEDIA_PREV_TRACK)
            return
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
        m.add_command(label="เล่น/พัก", command=self.cmd_playpause)
        m.add_command(label="เพลงถัดไป", command=self.cmd_next)
        m.add_command(label="เพลงก่อนหน้า", command=self.cmd_prev)
        m.add_separator()
        m.add_checkbutton(label="อยู่บนสุดเสมอ", variable=self._topmost_var,
                          command=self._apply_topmost)
        m.add_command(label="ซ่อนแถบนี้ (Ctrl+Alt+M)", command=lambda: self.hide(user=True))
        self.menu = m

    # ---------- คำสั่งควบคุม (เลือกวิธีตามโหมด) ----------
    def cmd_playpause(self):
        if self._mode == "audio" and not self._snap.get("title"):
            send_media_key(VK_MEDIA_PLAY_PAUSE)
        else:
            self.watcher.command("pause" if self._snap.get("playing") else "play")

    def cmd_next(self):
        if self._mode == "audio" and not self._snap.get("title"):
            send_media_key(VK_MEDIA_NEXT_TRACK)
        else:
            self.watcher.command("next")

    def cmd_prev(self):
        if self._mode == "audio" and not self._snap.get("title"):
            send_media_key(VK_MEDIA_PREV_TRACK)
        else:
            self.watcher.command("prev")

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
