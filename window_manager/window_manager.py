# -*- coding: utf-8 -*-
"""
Kuroya Window Manager
=====================
โปรแกรมจัดการหน้าต่างบน Windows (Windows-only)

ฟีเจอร์
- สแนปหน้าต่างเข้าโซนเลย์เอาต์แบบ FancyZones-lite:
    กด Ctrl+Alt+Z เพื่อเปิดผังโซนทั่วจอ แล้วกดเลข 1-9 หรือคลิกโซน
    เพื่อย้ายหน้าต่างที่กำลังใช้งานเข้าโซนนั้น
- ลากหน้าต่าง (จับที่แถบหัวข้อ) แล้ววางลงบนโซนได้โดยตรง
- แถบจัดการหน้าต่างแบบลอยที่ขอบล่างจอ: ค้นหา / สลับ / ย่อ / ขยาย / ปิด
- ฮอตคีย์ทั่วระบบ: Ctrl+Alt+←/→/↑/↓, Ctrl+Alt+1-9, Ctrl+Alt+0 (คืนตำแหน่งเดิม) ฯลฯ
- จำตำแหน่งเดิมของหน้าต่างก่อนสแนป กด Ctrl+Alt+0 เพื่อคืนกลับ
- บันทึกการตั้งค่า (เลย์เอาต์, ลาก-สแนป, ระยะเว้นโซน, ตำแหน่งแถบ) ลง settings.json

ใช้เฉพาะไลบรารีมาตรฐานของ Python (ctypes + tkinter) — ไม่ต้อง pip install อะไรเพิ่ม
รองรับ Windows 10/11 + Python 3.8+ (ต้องติดตั้ง Python แบบที่มี tkinter — ตัวติดตั้งจาก python.org มีให้ครับ)

วิธีรัน:  pythonw window_manager.py   (ไม่แสดงคอนโซล)
         python window_manager.py    (เห็น log/ข้อผิดพลาด เอาไว้ดีบัก)
"""
from __future__ import annotations

import ctypes
import json
import os
import queue
import sys
import threading
import time

try:
    import tkinter as tk
except ImportError:   # มีเฉพาะตอนรันจริงบน Windows; --check บนเครื่องอื่นไม่ต้องใช้
    tk = None

IS_WINDOWS = (os.name == "nt")

# ---------------------------------------------------------------------------
# ค่าคงที่ / ธีมสี / เลย์เอาต์โซน
# ---------------------------------------------------------------------------

APP_TITLE_PREFIX = "KuroyaWM"   # ใช้กรองหน้าต่างของโปรแกรมนี้เองออกจากรายการ

COLORS = {
    "bg":         "#17181d",
    "bg2":        "#1f2128",
    "row":        "#22242c",
    "row_active": "#2b4a63",
    "fg":         "#e8eaed",
    "muted":      "#9aa0a6",
    "accent":     "#4fc3f7",
    "accent2":    "#b39ddb",
    "danger":     "#ef5350",
    "zone_fill":  "#1e4e8c",
    "zone_hover": "#2f7fd1",
    "zone_line":  "#7dd3fc",
}

# เลย์เอาต์โซน: ค่า (x, y, w, h) เป็นสัดส่วน 0-1 ของพื้นที่ทำงานของจอ
LAYOUTS = {
    "halves":    {"name": "ครึ่งซ้าย–ขวา",      "zones": [(0.0, 0.0, 0.5, 1.0), (0.5, 0.0, 0.5, 1.0)]},
    "main_left": {"name": "หลัก ⅔ + เสริม ⅓",   "zones": [(0.0, 0.0, 2/3, 1.0), (2/3, 0.0, 1/3, 1.0)]},
    "thirds":    {"name": "สามคอลัมน์",         "zones": [(0.0, 0.0, 1/3, 1.0), (1/3, 0.0, 1/3, 1.0), (2/3, 0.0, 1/3, 1.0)]},
    "main_side": {"name": "หลัก 60% + ข้างคู่", "zones": [(0.0, 0.0, 0.6, 1.0), (0.6, 0.0, 0.2, 1.0), (0.8, 0.0, 0.2, 1.0)]},
    "grid22":    {"name": "ตาราง 2×2",          "zones": [(0.0, 0.0, 0.5, 0.5), (0.5, 0.0, 0.5, 0.5),
                                                           (0.0, 0.5, 0.5, 0.5), (0.5, 0.5, 0.5, 0.5)]},
    "grid23":    {"name": "ตาราง 3×2",          "zones": [(0.0, 0.0, 1/3, 0.5), (1/3, 0.0, 1/3, 0.5), (2/3, 0.0, 1/3, 0.5),
                                                           (0.0, 0.5, 1/3, 0.5), (1/3, 0.5, 1/3, 0.5), (2/3, 0.5, 1/3, 0.5)]},
    "full":      {"name": "เต็มจอ",             "zones": [(0.0, 0.0, 1.0, 1.0)]},
}
LAYOUT_ORDER = ["halves", "main_left", "thirds", "main_side", "grid22", "grid23", "full"]

GAP_CHOICES = [0, 4, 8, 12, 16]

# ค่าคงที่ Win32
WM_CLOSE = 0x0010
WM_QUIT = 0x0012
WM_HOTKEY = 0x0312
SW_MINIMIZE = 6
SW_MAXIMIZE = 3
SW_RESTORE = 9
HWND_TOP = 0
SWP_SHOWWINDOW = 0x0040
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_NOREPEAT = 0x4000
GA_ROOT = 2
DWMWA_CLOAKED = 14
VK_LBUTTON = 0x01
VK_MENU = 0x12
KEYEVENTF_KEYUP = 0x0002
MONITOR_DEFAULTTONEAREST = 2

WS_VISIBLE = 0x10000000
WS_CAPTION = 0x00C00000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000
GWL_STYLE = -16
GWL_EXSTYLE = -20


def ui_font(size=10, bold=False):
    """ฟอนต์ไทยที่มีในเครื่อง Windows (Leelawadee UI)"""
    return ("Leelawadee UI", size, "bold" if bold else "normal")


# ---------------------------------------------------------------------------
# ฟังก์ชันเรขาคณิตของโซน (pure functions — ทดสอบข้ามแพลตฟอร์มได้)
# ---------------------------------------------------------------------------

def compute_zone_rects(work, fractions, gap=8):
    """แปลงสัดส่วนโซนเป็นพิกเซลจริงบนพื้นที่ทำงานของจอ

    work      : (left, top, right, bottom) พื้นที่ทำงาน (ไม่รวม taskbar)
    fractions : รายการ (fx, fy, fw, fh) สัดส่วน
    gap       : ระยะเว้นระหว่างโซน (พิกเซล)
    คืนค่า    : รายการ (x, y, w, h) เป็นพิกเซล
    """
    x0, y0, x1, y1 = work
    W = max(0, x1 - x0)
    H = max(0, y1 - y0)
    g = max(0, int(gap))
    out = []
    for fx, fy, fw, fh in fractions:
        x = x0 + round(fx * W)
        y = y0 + round(fy * H)
        w = round(fw * W)
        h = round(fh * H)
        out.append((x + g // 2, y + g // 2, max(1, w - g), max(1, h - g)))
    return out


def zone_index_at(px, py, rects, tol=3):
    """จุด (px, py) อยู่ในโซนลำดับที่เท่าไร (0-based) — ไม่อยู่ในโซนไหนคืน None"""
    for i, (x, y, w, h) in enumerate(rects):
        if (x - tol) <= px <= (x + w + tol) and (y - tol) <= py <= (y + h + tol):
            return i
    return None


def window_occupies_zone(win_rect, zone_rect, tol=26):
    """หน้าต่างกำลังอยู่ในโซนนี้อยู่แล้วหรือไม่ (เทียบขอบทั้งสี่ด้านภายใน tolerance)"""
    wx0, wy0, wx1, wy1 = win_rect
    zx, zy, zw, zh = zone_rect
    return (abs(wx0 - zx) <= tol and abs(wy0 - zy) <= tol
            and abs(wx1 - (zx + zw)) <= tol and abs(wy1 - (zy + zh)) <= tol)


# ---------------------------------------------------------------------------
# การตั้งค่า (settings.json)
# ---------------------------------------------------------------------------

DEFAULT_SETTINGS = {
    "layout": "halves",     # เลย์เอาต์โซนปัจจุบัน
    "drag_snap": True,      # ลากหน้าต่างไปวางบนโซน
    "gap_px": 8,            # ระยะเว้นระหว่างโซน
    "panel_x": None,        # ตำแหน่งแถบจัดการหน้าต่าง (จำจากการลาก)
    "panel_y": None,
}


def script_dir():
    return os.path.dirname(os.path.abspath(__file__))


def settings_path():
    return os.path.join(script_dir(), "settings.json")


def load_settings(path=settings_path()):
    s = dict(DEFAULT_SETTINGS)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            s.update({k: v for k, v in data.items() if k in DEFAULT_SETTINGS})
    except Exception:
        pass
    if s["layout"] not in LAYOUTS:
        s["layout"] = "halves"
    if s["gap_px"] not in GAP_CHOICES:
        s["gap_px"] = 8
    return s


def save_settings(settings, path=settings_path()):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Win32 API layer (ctypes) — โหลดเฉพาะตอนรันบน Windows เท่านั้น
# ---------------------------------------------------------------------------

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("rcMonitor", RECT), ("rcWork", RECT),
                ("dwFlags", ctypes.c_uint)]


class WINDOWPLACEMENT(ctypes.Structure):
    _fields_ = [("length", ctypes.c_uint), ("flags", ctypes.c_uint),
                ("showCmd", ctypes.c_uint), ("ptMinPosition", POINT),
                ("ptMaxPosition", POINT), ("rcNormalPosition", RECT)]


class MSG(ctypes.Structure):
    _fields_ = [("hwnd", ctypes.c_void_p), ("message", ctypes.c_uint),
                ("wParam", ctypes.c_size_t), ("lParam", ctypes.c_ssize_t),
                ("time", ctypes.c_uint), ("pt", POINT)]


HWND = ctypes.c_void_p
DWORD = ctypes.c_uint
UINT = ctypes.c_uint
BOOL = ctypes.c_int

if IS_WINDOWS:
    WNDENUMPROC = ctypes.WINFUNCTYPE(BOOL, HWND, ctypes.c_void_p)
    MONITORENUMPROC = ctypes.WINFUNCTYPE(BOOL, ctypes.c_void_p, ctypes.c_void_p,
                                         ctypes.POINTER(RECT), ctypes.c_void_p)
else:   # บน OS อื่นไม่จำเป็น (ใช้เฉพาะตอนรันจริง) — ประกาศ None เพื่อ import ได้
    WNDENUMPROC = None
    MONITORENUMPROC = None


class WindowInfo:
    """ข้อมูลหน้าต่างหนึ่งบานสำหรับแสดงในแถบ"""
    __slots__ = ("hwnd", "title", "minimized", "is_maximized", "rect")

    def __init__(self, hwnd, title, minimized, is_maximized, rect):
        self.hwnd = hwnd
        self.title = title
        self.minimized = minimized
        self.is_maximized = is_maximized
        self.rect = rect


class Monitor:
    """ข้อมูลจอหนึ่งหน้า"""
    __slots__ = ("handle", "full", "work", "is_primary")

    def __init__(self, handle, full, work, is_primary):
        self.handle = handle
        self.full = full        # (x, y, w, h) ทั้งจอ
        self.work = work        # (x, y, w, h) พื้นที่ทำงาน (ตัด taskbar)
        self.is_primary = is_primary


class HotkeyDef:
    __slots__ = ("id", "name", "extra", "mods", "vk", "label")

    def __init__(self, hid, name, extra, mods, vk, label):
        self.id = hid
        self.name = name
        self.extra = extra
        self.mods = mods
        self.vk = vk
        self.label = label


def _build_hotkeys():
    defs = []
    nid = [1]

    def add(name, vk, label, extra=None):
        defs.append(HotkeyDef(nid[0], name, extra, MOD_CONTROL | MOD_ALT, vk, label))
        nid[0] += 1

    add("toggle_overlay", 0x5A, "Ctrl+Alt+Z — เปิด/ปิดผังโซน")
    add("snap_left",   0x25, "Ctrl+Alt+← — สแนปครึ่งซ้าย")
    add("snap_right",  0x27, "Ctrl+Alt+→ — สแนปครึ่งขวา")
    add("maximize",    0x26, "Ctrl+Alt+↑ — ขยายเต็มจอ")
    add("minimize",    0x28, "Ctrl+Alt+↓ — ย่อหน้าต่าง")
    add("unsnap",      0x30, "Ctrl+Alt+0 — คืนตำแหน่งเดิม")
    for i in range(1, 10):
        add("zone", 0x30 + i, f"Ctrl+Alt+{i} — สแนปเข้าโซน {i}", extra=i)
    add("cycle_layout", 0x4C, "Ctrl+Alt+L — สลับเลย์เอาต์")
    add("toggle_panel", 0x53, "Ctrl+Alt+S — ซ่อน/แสดงแถบหน้าต่าง")
    add("minimize_all", 0x44, "Ctrl+Alt+D — ย่อทุกหน้าต่าง")
    add("quit",         0x51, "Ctrl+Alt+Q — ออกจากโปรแกรม")
    return defs


HOTKEYS = _build_hotkeys()
HOTKEY_BY_ID = {h.id: h for h in HOTKEYS}


class WinAPI:
    """ครอบ Win32 API ที่จำเป็นด้วย ctypes (กำหนด argtypes กัน hwnd โดนตัด 32-bit)"""

    def __init__(self):
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        try:
            self.dwmapi = ctypes.WinDLL("dwmapi")
        except Exception:
            self.dwmapi = None
        try:
            self.shcore = ctypes.WinDLL("shcore")
        except Exception:
            self.shcore = None

        u = self.user32
        k = self.kernel32
        _sig = lambda fn, rest, *args: (setattr(fn, "restype", rest),
                                        setattr(fn, "argtypes", args))
        _sig(u.EnumWindows, BOOL, WNDENUMPROC, ctypes.c_void_p)
        _sig(u.GetWindowTextLengthW, ctypes.c_int, HWND)
        _sig(u.GetWindowTextW, ctypes.c_int, HWND, ctypes.c_wchar_p, ctypes.c_int)
        _sig(u.IsWindowVisible, BOOL, HWND)
        _sig(u.IsWindow, BOOL, HWND)
        _sig(u.IsIconic, BOOL, HWND)
        _sig(u.IsZoomed, BOOL, HWND)
        _sig(u.GetWindowLongW, ctypes.c_long, HWND, ctypes.c_int)
        _sig(u.GetWindowRect, BOOL, HWND, ctypes.POINTER(RECT))
        _sig(u.GetAncestor, HWND, HWND, UINT)
        _sig(u.GetForegroundWindow, HWND)
        _sig(u.SetForegroundWindow, BOOL, HWND)
        _sig(u.BringWindowToTop, BOOL, HWND)
        _sig(u.ShowWindow, BOOL, HWND, ctypes.c_int)
        _sig(u.MoveWindow, BOOL, HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int,
             ctypes.c_int, BOOL)
        _sig(u.SetWindowPos, BOOL, HWND, HWND, ctypes.c_int, ctypes.c_int,
             ctypes.c_int, ctypes.c_int, UINT)
        _sig(u.PostMessageW, BOOL, HWND, UINT, ctypes.c_size_t, ctypes.c_ssize_t)
        _sig(u.GetWindowThreadProcessId, DWORD, HWND, ctypes.POINTER(DWORD))
        _sig(u.AttachThreadInput, BOOL, DWORD, DWORD, BOOL)
        _sig(u.keybd_event, None, ctypes.c_ubyte, ctypes.c_ubyte, DWORD, ctypes.c_size_t)
        _sig(u.GetCursorPos, BOOL, ctypes.POINTER(POINT))
        _sig(u.GetAsyncKeyState, ctypes.c_short, ctypes.c_int)
        _sig(u.WindowFromPoint, HWND, POINT)
        _sig(u.MonitorFromWindow, ctypes.c_void_p, HWND, DWORD)
        _sig(u.MonitorFromPoint, ctypes.c_void_p, POINT, DWORD)
        _sig(u.EnumDisplayMonitors, BOOL, ctypes.c_void_p, ctypes.POINTER(RECT),
             MONITORENUMPROC, ctypes.c_void_p)
        _sig(u.GetMonitorInfoW, BOOL, ctypes.c_void_p, ctypes.POINTER(MONITORINFO))
        _sig(u.GetWindowPlacement, BOOL, HWND, ctypes.POINTER(WINDOWPLACEMENT))
        _sig(u.RegisterHotKey, BOOL, HWND, ctypes.c_int, UINT, UINT)
        _sig(u.UnregisterHotKey, BOOL, HWND, ctypes.c_int)
        _sig(u.GetMessageW, ctypes.c_int, ctypes.POINTER(MSG), HWND, UINT, UINT)
        _sig(u.PostThreadMessageW, BOOL, DWORD, UINT, ctypes.c_size_t, ctypes.c_ssize_t)
        _sig(k.GetCurrentThreadId, DWORD)
        _sig(k.CreateMutexW, ctypes.c_void_p, ctypes.c_void_p, BOOL, ctypes.c_wchar_p)

        # DPI awareness — ให้พิกัดตรงกับพิกเซลจริงบนจอ HiDPI
        try:
            self.shcore.SetProcessDpiAwareness(2)   # PER_MONITOR_DPI_AWARE
        except Exception:
            try:
                u.SetProcessDPIAware()
            except Exception:
                pass

        self._mutex = None

    # ---------- single instance ----------
    def try_acquire_mutex(self):
        self._mutex = self.kernel32.CreateMutexW(None, False, "KuroyaWM_SingleInstance")
        return ctypes.get_last_error() != 183   # 183 = ERROR_ALREADY_EXISTS

    # ---------- จอ ----------
    def _monitorinfo_to_monitor(self, hmon, mi):
        fx, fy, fr, fb = mi.rcMonitor.left, mi.rcMonitor.top, mi.rcMonitor.right, mi.rcMonitor.bottom
        wx, wy, wr, wb = mi.rcWork.left, mi.rcWork.top, mi.rcWork.right, mi.rcWork.bottom
        return Monitor(hmon, (fx, fy, fr - fx, fb - fy), (wx, wy, wr - wx, wb - wy),
                       bool(mi.dwFlags & 1))

    def monitors(self):
        out = []
        u = self.user32

        def cb(hmon, _hdc, _lprc, _data):
            mi = MONITORINFO()
            mi.cbSize = ctypes.sizeof(MONITORINFO)
            if u.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                out.append(self._monitorinfo_to_monitor(hmon, mi))
            return True

        u.EnumDisplayMonitors(None, None, MONITORENUMPROC(cb), None)
        out.sort(key=lambda m: (not m.is_primary))
        return out

    def primary_monitor(self):
        mons = self.monitors()
        return mons[0] if mons else None

    def monitor_from_window(self, hwnd):
        u = self.user32
        hmon = u.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
        return self._monitor_by_handle(hmon)

    def monitor_from_point(self, px, py):
        u = self.user32
        pt = POINT(int(px), int(py))
        hmon = u.MonitorFromPoint(pt, MONITOR_DEFAULTTONEAREST)
        return self._monitor_by_handle(hmon)

    def _monitor_by_handle(self, hmon):
        if not hmon:
            return self.primary_monitor()
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if self.user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            return self._monitorinfo_to_monitor(hmon, mi)
        return self.primary_monitor()

    # ---------- หน้าต่าง ----------
    def is_window(self, hwnd):
        return bool(hwnd) and bool(self.user32.IsWindow(hwnd))

    def window_title(self, hwnd):
        n = self.user32.GetWindowTextLengthW(hwnd)
        if n <= 0:
            return ""
        buf = ctypes.create_unicode_buffer(n + 1)
        self.user32.GetWindowTextW(hwnd, buf, n + 1)
        return buf.value.strip()

    def is_our_window(self, hwnd):
        return self.window_title(hwnd).startswith(APP_TITLE_PREFIX)

    def is_cloaked(self, hwnd):
        if not self.dwmapi:
            return False
        v = ctypes.c_uint(0)
        try:
            hr = self.dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED,
                                                   ctypes.byref(v), ctypes.sizeof(v))
        except Exception:
            return False
        return hr == 0 and v.value != 0

    def window_rect(self, hwnd):
        r = RECT()
        if self.user32.GetWindowRect(hwnd, ctypes.byref(r)):
            return (r.left, r.top, r.right, r.bottom)
        return None

    def normal_rect(self, hwnd):
        """ตำแหน่ง/ขนาดปกติ (ตอนไม่ย่อ/ไม่ขยายเต็ม) ของหน้าต่าง"""
        wp = WINDOWPLACEMENT()
        wp.length = ctypes.sizeof(WINDOWPLACEMENT)
        if self.user32.GetWindowPlacement(hwnd, ctypes.byref(wp)):
            r = wp.rcNormalPosition
            return (r.left, r.top, r.right, r.bottom)
        return None

    def enumerate_windows(self):
        """รายชื่อหน้าต่างแอปจริง (เรียงตาม z-order บนสุดก่อน) สำหรับแสดงในแถบ"""
        out = []
        u = self.user32

        def on_window(hwnd, _lparam):
            try:
                if not u.IsWindowVisible(hwnd):
                    return True
                style = u.GetWindowLongW(hwnd, GWL_STYLE)
                ex = u.GetWindowLongW(hwnd, GWL_EXSTYLE)
                appwindow = bool(ex & WS_EX_APPWINDOW)
                if bool(ex & WS_EX_TOOLWINDOW) and not appwindow:
                    return True
                if not (bool(style & WS_CAPTION) or appwindow):
                    return True
                if self.is_cloaked(hwnd):
                    return True
                if u.GetAncestor(hwnd, GA_ROOT) != hwnd:
                    return True
                title = self.window_title(hwnd)
                if not title or title.startswith(APP_TITLE_PREFIX):
                    return True
                rect = self.window_rect(hwnd)
                if rect is None:
                    return True
                out.append(WindowInfo(hwnd, title, bool(u.IsIconic(hwnd)),
                                      bool(u.IsZoomed(hwnd)), rect))
            except Exception:
                pass
            return True

        u.EnumWindows(WNDENUMPROC(on_window), None)
        return out

    def foreground_hwnd(self):
        return self.user32.GetForegroundWindow() or None

    def window_from_point(self, px, py):
        return self.user32.WindowFromPoint(POINT(int(px), int(py))) or None

    def show_window(self, hwnd, cmd):
        return self.user32.ShowWindow(hwnd, cmd)

    def close_window(self, hwnd):
        return self.user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)

    def move_window(self, hwnd, rect):
        x0, y0, x1, y1 = rect
        return self.user32.MoveWindow(hwnd, int(x0), int(y0),
                                      max(1, int(x1 - x0)), max(1, int(y1 - y0)), True)

    def snap_window(self, hwnd, x, y, w, h):
        """ย้ายหน้าต่างเข้าโซน: คืนสภาพก่อนถ้าย่อ/ขยายอยู่ แล้ววางตรงตำแหน่ง"""
        u = self.user32
        if not self.is_window(hwnd):
            return False
        if u.IsIconic(hwnd):
            u.ShowWindow(hwnd, SW_RESTORE)
            time.sleep(0.05)
        elif u.IsZoomed(hwnd):
            u.ShowWindow(hwnd, SW_RESTORE)
            time.sleep(0.05)
        u.SetWindowPos(hwnd, HWND_TOP, int(x), int(y), int(w), int(h), SWP_SHOWWINDOW)
        u.SetForegroundWindow(hwnd)
        return True

    def force_foreground(self, hwnd):
        """ดึงหน้าต่างขึ้นมาใช้งานจริง ๆ (Windows เข้มงวดเรื่อง SetForegroundWindow)"""
        u = self.user32
        if not self.is_window(hwnd):
            return False
        if u.IsIconic(hwnd):
            u.ShowWindow(hwnd, SW_RESTORE)
            time.sleep(0.06)
        this_tid = self.kernel32.GetCurrentThreadId()
        fg = u.GetForegroundWindow()
        fg_tid = u.GetWindowThreadProcessId(fg, None) if fg else 0
        target_tid = u.GetWindowThreadProcessId(hwnd, None)
        attached = []
        for tid in {fg_tid, target_tid}:
            if tid and tid != this_tid and u.AttachThreadInput(this_tid, tid, True):
                attached.append(tid)
        u.BringWindowToTop(hwnd)
        ok = bool(u.SetForegroundWindow(hwnd))
        for tid in attached:
            u.AttachThreadInput(this_tid, tid, False)
        if not ok:
            # เทคนิคกดปุ่ม Alt แวบหนึ่งเพื่อผ่านเงื่อนไข foreground ของ Windows
            u.keybd_event(VK_MENU, 0, 0, 0)
            u.SetForegroundWindow(hwnd)
            u.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
        return True

    # ---------- ฮอตคีย์ ----------
    def register_hotkey(self, hid, mods, vk):
        return bool(self.user32.RegisterHotKey(None, hid, mods | MOD_NOREPEAT, vk))

    def unregister_hotkey(self, hid):
        self.user32.UnregisterHotKey(None, hid)

    def post_thread_quit(self, tid):
        self.user32.PostThreadMessageW(tid, WM_QUIT, 0, 0)

    def current_thread_id(self):
        return self.kernel32.GetCurrentThreadId()


# ---------------------------------------------------------------------------
# เธรดลงทะเบียน + รับฮอตคีย์ทั่วระบบ
# ---------------------------------------------------------------------------

class HotkeyThread(threading.Thread):
    def __init__(self, api, cmd_q, dispatch):
        super().__init__(daemon=True, name="kuroya-hotkeys")
        self.api = api
        self.cmd_q = cmd_q
        self.dispatch = dispatch
        self.thread_id = 0
        self.failed = []
        self._registered = []
        self._ready_cb = None

    def set_ready_cb(self, cb):
        self._ready_cb = cb

    def run(self):
        self.thread_id = self.api.current_thread_id()
        for hk in HOTKEYS:
            if self.api.register_hotkey(hk.id, hk.mods, hk.vk):
                self._registered.append(hk)
            else:
                self.failed.append(hk)
        if self._ready_cb:
            self.cmd_q.put(lambda: self._ready_cb(list(self.failed)))
        msg = MSG()
        u = self.api.user32
        while True:
            r = u.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if r <= 0:
                break
            if msg.message == WM_HOTKEY:
                hk = HOTKEY_BY_ID.get(int(msg.wParam))
                if hk:
                    self.cmd_q.put(lambda n=hk.name, e=hk.extra: self.dispatch(n, e))
        for hk in self._registered:
            try:
                self.api.unregister_hotkey(hk.id)
            except Exception:
                pass

    def stop(self):
        if self.thread_id:
            self.api.post_thread_quit(self.thread_id)


# ---------------------------------------------------------------------------
# เธรดตรวจจับการลากหน้าต่างไปวางบนโซน (FancyZones-lite)
# หลักการ: ถ้ากดเมาส์ซ้ายค้างที่แถบหัวข้อของหน้าต่างแล้วลากเกินระยะหนึ่ง
# จะแสดงผังโซนขึ้นมา และเมื่อปล่อยเมาส์บนโซนใด หน้าต่างจะถูกสแนปเข้าโซนนั้น
# ---------------------------------------------------------------------------

class DragSnapThread(threading.Thread):
    DRAG_MIN_DIST2 = 3600     # ลากเกิน ~60px ถึงจะถือว่าเป็นการลาก
    TITLEBAR_H = 44           # จับเฉพาะที่แถบหัวข้อ (ระยะจากขอบบนหน้าต่าง)

    def __init__(self, api, settings, cmd_q):
        super().__init__(daemon=True, name="kuroya-dragsnap")
        self.api = api
        self.settings = settings
        self.cmd_q = cmd_q
        self._stop_evt = threading.Event()

    def stop(self):
        self._stop_evt.set()

    def run(self):
        u = self.api.user32
        state = None
        while not self._stop_evt.is_set():
            time.sleep(0.10)
            try:
                if not self.settings.get("drag_snap", True):
                    state = None
                    continue
                down = (u.GetAsyncKeyState(VK_LBUTTON) & 0x8000) != 0
                pt = POINT()
                if not u.GetCursorPos(ctypes.byref(pt)):
                    state = None
                    continue
                px, py = pt.x, pt.y

                if down and state is None:
                    state = self._begin_drag(px, py)
                elif down and state:
                    self._during_drag(state, px, py)
                elif (not down) and state:
                    self._end_drag(state, px, py)
                    state = None
            except Exception:
                state = None

    def _begin_drag(self, px, py):
        hwnd = self.api.foreground_hwnd()
        if not hwnd or self.api.is_our_window(hwnd):
            return None
        style = self.api.user32.GetWindowLongW(hwnd, GWL_STYLE)
        if not (style & WS_CAPTION):
            return None
        r = self.api.window_rect(hwnd)
        if not r:
            return None
        on_titlebar = (r[1] <= py <= r[1] + self.TITLEBAR_H and r[0] <= px <= r[2])
        if not on_titlebar:
            return None
        return {"hwnd": hwnd, "sx": px, "sy": py,
                "lx": px, "ly": py, "shown": False,
                "mon": None, "rects": None, "zone": None}

    def _during_drag(self, state, px, py):
        if not state["shown"]:
            d2 = (px - state["sx"]) ** 2 + (py - state["sy"]) ** 2
            if d2 < self.DRAG_MIN_DIST2:
                return
            mon = self.api.monitor_from_point(px, py)
            if not mon:
                return
            state["mon"] = mon
            state["rects"] = self._zone_rects(mon)
            state["shown"] = True
            self.cmd_q.put(lambda m=mon: self.app_overlay_show(m))
        else:
            mon = self.api.monitor_from_point(px, py)
            if mon and state["mon"] and mon.full != state["mon"].full:
                state["mon"] = mon
                state["rects"] = self._zone_rects(mon)
                self.cmd_q.put(lambda m=mon: self.app_overlay_show(m))
        if state["shown"] and state["rects"]:
            idx = zone_index_at(px, py, state["rects"])
            if idx != state["zone"]:
                state["zone"] = idx
                self.cmd_q.put(lambda i=idx: self.app_overlay_hover(i))

    def _end_drag(self, state, px, py):
        if state["shown"] and state["rects"]:
            idx = zone_index_at(px, py, state["rects"])
            self.cmd_q.put(lambda: self.app_overlay_hide())
            if idx is not None:
                hwnd, mon = state["hwnd"], state["mon"]
                self.cmd_q.put(lambda h=hwnd, i=idx, m=mon:
                               self.app_snap_to_zone(h, i, m))
        state["shown"] = False

    def _zone_rects(self, mon):
        key = self.settings.get("layout", "halves")
        fractions = LAYOUTS.get(key, LAYOUTS["halves"])["zones"]
        gap = int(self.settings.get("gap_px", 8))
        return compute_zone_rects(mon.work, fractions, gap)

    # เดทเท็คเตอร์รันในเธรดอื่น — ส่งคำสั่งเข้าคิวให้ UI เธรดเป็นคนเรียกจริง
    def app_overlay_show(self, mon):
        raise NotImplementedError  # replaced ตอนสร้างด้วย bind_app()

    def app_overlay_hover(self, idx):
        raise NotImplementedError

    def app_overlay_hide(self):
        raise NotImplementedError

    def app_snap_to_zone(self, hwnd, idx, mon):
        raise NotImplementedError

    def bind_app(self, show, hover, hide, snap):
        self.app_overlay_show = show
        self.app_overlay_hover = hover
        self.app_overlay_hide = hide
        self.app_snap_to_zone = snap


# ---------------------------------------------------------------------------
# ผังโซนโปร่งใสเต็มจอ (overlay)
# ---------------------------------------------------------------------------

class ZoneOverlay:
    def __init__(self, app):
        self.app = app
        self.win = None
        self.canvas = None
        self.mode = None          # "manual" | "drag" | "toast"
        self.target = None        # hwnd ที่จะสแนปเมื่อคลิกโซน/กดเลข
        self.mon = None
        self.rects = []
        self.zone_items = []
        self.highlight = None
        self._timer = None

    def _build(self):
        win = tk.Toplevel(self.app.root)
        win.title(APP_TITLE_PREFIX + "-Overlay")
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(bg="#000000")
        self.canvas = tk.Canvas(win, highlightthickness=0, bg="#000000")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self._on_click)
        win.bind("<Escape>", lambda e: self.hide())
        win.bind("<Key>", self._on_key)
        win.withdraw()
        self.win = win
        return win

    # ----- การแสดงผล -----
    def show_manual(self, mon, target):
        self._show(mon, mode="manual", target=target)
        self._auto_hide(10000)

    def show_drag(self, mon):
        self._show(mon, mode="drag", target=None)

    def show_toast(self, mon, text):
        self._show(mon, mode="toast", target=None, toast_text=text)
        self._auto_hide(1400)

    def _show(self, mon, mode, target, toast_text=None):
        win = self.win if (self.win and self.win.winfo_exists()) else self._build()
        self.mode = mode
        self.target = target
        self.mon = mon
        x, y, w, h = mon.full
        win.geometry(f"{w}x{h}+{x}+{y}")
        key = self.app.settings.get("layout", "halves")
        fractions = LAYOUTS.get(key, LAYOUTS["halves"])["zones"]
        gap = int(self.app.settings.get("gap_px", 8))
        self.rects = compute_zone_rects(mon.work, fractions, gap)
        self.highlight = None
        self._draw(toast_text)
        win.attributes("-alpha", 0.42 if mode == "toast" else 0.30)
        win.deiconify()
        win.lift()
        win.attributes("-topmost", True)
        if mode == "manual":
            try:
                win.focus_force()
            except Exception:
                pass

    def _draw(self, toast_text=None):
        c = self.canvas
        c.delete("all")
        if toast_text is not None:
            _, _, w, h = self.mon.full
            cx, cy = w // 2, h // 2
            c.create_rectangle(cx - 230, cy - 44, cx + 230, cy + 44,
                               fill=COLORS["bg2"], outline=COLORS["accent"], width=2)
            c.create_text(cx, cy, text=toast_text, fill=COLORS["fg"], font=ui_font(13, True))
            return
        self.zone_items = []
        for i, (x, y, zw, zh) in enumerate(self.rects):
            item = c.create_rectangle(x, y, x + zw, y + zh,
                                      fill=COLORS["zone_fill"],
                                      outline=COLORS["zone_line"], width=2)
            self.zone_items.append(item)
            c.create_text(x + zw // 2, y + zh // 2 - 16, text=str(i + 1),
                          fill="#ffffff", font=ui_font(28, True))
        layout_name = LAYOUTS.get(self.app.settings.get("layout", "halves"),
                                  {}).get("name", "")
        _, _, w, h = self.mon.full
        c.create_text(14, 12, anchor="nw",
                      text=f"เลย์เอาต์: {layout_name} — คลิกโซนหรือกดเลข 1-{len(self.rects)} • Esc ปิด",
                      fill=COLORS["zone_line"], font=ui_font(11, True))

    def drag_hover(self, idx):
        if self.mode != "drag" or not (self.win and self.win.winfo_exists()):
            return
        if idx == self.highlight:
            return
        if self.highlight is not None and self.highlight < len(self.zone_items):
            self.canvas.itemconfigure(self.zone_items[self.highlight],
                                      fill=COLORS["zone_fill"])
        self.highlight = idx
        if idx is not None and idx < len(self.zone_items):
            self.canvas.itemconfigure(self.zone_items[idx],
                                      fill=COLORS["zone_hover"])

    def visible(self):
        return bool(self.win and self.win.winfo_exists()
                    and self.win.state() == "normal")

    def hide(self):
        if self._timer:
            try:
                self.app.root.after_cancel(self._timer)
            except Exception:
                pass
            self._timer = None
        if self.win and self.win.winfo_exists():
            self.win.withdraw()
        self.mode = None
        self.target = None

    def _auto_hide(self, ms):
        if self._timer:
            try:
                self.app.root.after_cancel(self._timer)
            except Exception:
                pass
        self._timer = self.app.root.after(ms, self.hide)

    # ----- อินพุตบน overlay (โหมด manual) -----
    def _on_click(self, event):
        if self.mode == "manual" and self.target:
            idx = zone_index_at(event.x, event.y, self.rects)
            if idx is not None:
                self.app.snap_window_to_zone(self.target, idx, monitor=self.mon)
        self.hide()

    def _on_key(self, event):
        if self.mode != "manual":
            return
        ch = getattr(event, "char", "") or ""
        if ch.isdigit() and int(ch) >= 1 and self.target:
            idx = int(ch) - 1
            if idx < len(self.rects):
                self.app.snap_window_to_zone(self.target, idx, monitor=self.mon)
            self.hide()


# ---------------------------------------------------------------------------
# แถบจัดการหน้าต่าง (หน้าต่างหลักของโปรแกรม)
# ---------------------------------------------------------------------------

class PanelApp:
    PANEL_W = 470
    LIST_H = 282

    def __init__(self, api):
        self.api = api
        self.settings_path = settings_path()
        self.settings = load_settings(self.settings_path)
        self.cmd_q = queue.Queue()
        self.original_rects = {}   # hwnd -> (x0,y0,x1,y1) ก่อนสแนปครั้งแรก
        self._windows = []
        self._rows = {}            # hwnd -> dict(widget refs)
        self._row_sig = None
        self._filter = ""
        self._last_fg = None
        self.failed_hotkeys = []
        self.tab = None

        self.root = tk.Tk()
        self.root.title(APP_TITLE_PREFIX + "-Panel")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=COLORS["bg"])
        self.root.resizable(False, False)

        self.overlay = ZoneOverlay(self)
        self._build_ui()
        self.menu = self._build_menu()
        self._place_initial()

        self.hotkeys = HotkeyThread(self.api, self.cmd_q, self._dispatch_hotkey)
        self.hotkeys.set_ready_cb(self._hotkeys_ready)
        self.drag = DragSnapThread(self.api, self.settings, self.cmd_q)
        self.drag.bind_app(self.overlay.show_drag, self.overlay.drag_hover,
                           self.overlay.hide, self._drag_snap_apply)

    # ================= UI =================
    def _build_ui(self):
        c = COLORS
        root = self.root
        root.configure(bg=c["bg"])

        # --- แถบหัว (ลากย้ายแถบได้จากตรงนี้) ---
        header = tk.Frame(root, bg=c["bg2"], padx=8, pady=6)
        header.pack(fill="x")
        header.bind("<Button-1>", self._header_press)
        header.bind("<B1-Motion>", self._header_drag)
        header.bind("<ButtonRelease-1>", self._header_release)

        self.title_lbl = tk.Label(header, text=" ⊞ Kuroya Window Manager",
                                  bg=c["bg2"], fg=c["accent"], font=ui_font(11, True))
        self.title_lbl.pack(side="left")
        self.title_lbl.bind("<Button-1>", self._header_press)
        self.title_lbl.bind("<B1-Motion>", self._header_drag)
        self.title_lbl.bind("<ButtonRelease-1>", self._header_release)
        self.title_lbl.bind("<Button-3>", self._show_menu)

        btn_kw = {"bd": 0, "relief": "flat", "cursor": "hand2", "font": ui_font(9)}
        zone_btn = tk.Label(header, text="ผังโซน", bg=c["bg2"], fg=c["fg"],
                            padx=8, **btn_kw)
        zone_btn.pack(side="right")
        self._hover(zone_btn, c["accent2"])
        zone_btn.bind("<Button-1>", lambda e: self.toggle_overlay())

        self.layout_btn = tk.Label(header, text="", bg=c["bg2"], fg=c["fg"],
                                   padx=8, **btn_kw)
        self.layout_btn.pack(side="right")
        self._hover(self.layout_btn, c["accent2"])
        self.layout_btn.bind("<Button-1>", lambda e: self.cycle_layout())
        self.layout_btn.bind("<Button-3>", self._show_menu)
        self._update_layout_button()

        collapse_btn = tk.Label(header, text="–", bg=c["bg2"], fg=c["fg"],
                                padx=8, **btn_kw)
        collapse_btn.pack(side="right")
        self._hover(collapse_btn, c["accent2"])
        collapse_btn.bind("<Button-1>", lambda e: self.hide_panel())

        quit_btn = tk.Label(header, text="✕", bg=c["bg2"], fg=c["fg"], padx=8, **btn_kw)
        quit_btn.pack(side="right")
        self._hover(quit_btn, c["danger"])
        quit_btn.bind("<Button-1>", lambda e: self.quit_app())

        # --- แถวค้นหา + ปุ่มลัด ---
        searchrow = tk.Frame(root, bg=c["bg"], padx=8, pady=6)
        searchrow.pack(fill="x")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search)
        self.search_entry = tk.Entry(searchrow, textvariable=self.search_var,
                                     bg=c["bg2"], fg=c["fg"], insertbackground=c["fg"],
                                     bd=0, font=ui_font(10), width=30)
        self.search_entry.insert(0, "ค้นหาหน้าต่าง…")
        self.search_entry.configure(fg=c["muted"])
        self.search_entry.pack(side="left", fill="x", expand=True, ipady=5)
        self.search_entry.bind("<FocusIn>", self._search_focus_in)
        self.search_entry.bind("<FocusOut>", self._search_focus_out)

        minall_btn = tk.Label(searchrow, text="ย่อทั้งหมด", bg=c["bg2"], fg=c["fg"],
                              padx=10, **btn_kw)
        minall_btn.pack(side="right")
        self._hover(minall_btn, c["accent"])
        minall_btn.bind("<Button-1>", lambda e: self.minimize_all())

        # --- รายการหน้าต่าง ---
        listwrap = tk.Frame(root, bg=c["bg"])
        listwrap.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(listwrap, bg=c["bg"], bd=0, highlightthickness=0,
                                height=self.LIST_H)
        self.canvas.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(listwrap, orient="vertical", command=self.canvas.yview,
                          bg=c["bg2"], troughcolor=c["bg"], bd=0,
                          activebackground=c["accent"])
        sb.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=sb.set)
        self.inner = tk.Frame(self.canvas, bg=c["bg"])
        self.canvas.create_window((0, 0), window=self.inner, anchor="nw", tags="inner")
        self.inner.bind("<Configure>",
                        lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(
            "inner", width=e.width))
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)
        root.bind("<Button-3>", self._show_menu)

        # --- แถบสถานะ ---
        self.status_lbl = tk.Label(root, text="", bg=c["bg"], fg=c["muted"],
                                   font=ui_font(8), anchor="w", padx=10, pady=4)
        self.status_lbl.pack(fill="x")
        self._set_default_status()

        self.empty_lbl = None

    def _make_icon(self, parent, text, hover_color, on_click, base_bg=None):
        c = COLORS
        lbl = tk.Label(parent, text=text, bg=base_bg or c["row"], fg=c["muted"],
                       bd=0, relief="flat", cursor="hand2",
                       font=ui_font(10, True), width=3, padx=2)
        lbl.pack(side="right", padx=1)
        self._hover(lbl, hover_color)
        lbl.bind("<Button-1>", lambda e: on_click())
        return lbl

    def _hover(self, widget, hover_fg):
        normal = widget.cget("fg")
        widget.bind("<Enter>", lambda e: widget.configure(fg=hover_fg))
        widget.bind("<Leave>", lambda e: widget.configure(fg=normal))

    def _on_wheel(self, event):
        self.canvas.yview_scroll(-1 * (event.delta // 120), "units")

    def _build_menu(self):
        m = tk.Menu(self.root, tearoff=0, bg=COLORS["bg2"], fg=COLORS["fg"],
                    font=ui_font(9), activebackground=COLORS["row_active"],
                    activeforeground=COLORS["fg"], bd=0)
        layout_menu = tk.Menu(m, tearoff=0, bg=COLORS["bg2"], fg=COLORS["fg"],
                              font=ui_font(9),
                              activebackground=COLORS["row_active"])
        for key in LAYOUT_ORDER:
            layout_menu.add_radiobutton(label=LAYOUTS[key]["name"],
                                        command=lambda k=key: self.set_layout(k))
        m.add_cascade(label="เลย์เอาต์โซน ▸", menu=layout_menu)
        m.add_checkbutton(label="ลากหน้าต่างไปวางบนโซน",
                          command=self.toggle_drag_snap)
        m.add_command(label="เปลี่ยนระยะเว้นโซน (คลิกเพื่อวนค่า)",
                      command=self.cycle_gap)
        m.add_separator()
        m.add_command(label="คืนตำแหน่งเดิมหน้าต่างที่ใช้งาน (Ctrl+Alt+0)",
                      command=self.unsnap_active)
        m.add_command(label="ย่อทุกหน้าต่าง (Ctrl+Alt+D)",
                      command=self.minimize_all)
        m.add_separator()
        m.add_command(label="ออกจากโปรแกรม (Ctrl+Alt+Q)",
                      command=self.quit_app)
        return m

    def _show_menu(self, event=None):
        try:
            # เตรียมสถานะ radio/check (index ตามลำดับ add_* ด้านบน)
            self.menu.entryconfigure(0, label=f"เลย์เอาต์โซน ▸  (ปัจจุบัน: "
                                     f"{LAYOUTS[self.settings['layout']]['name']})")
            self.menu.entryconfigure(1, label=f"ลากหน้าต่างไปวางบนโซน: "
                                     f"{'เปิด' if self.settings.get('drag_snap') else 'ปิด'}")
            self.menu.entryconfigure(2, label=f"ระยะเว้นโซน: {self.settings.get('gap_px', 8)}px "
                                     "(คลิกเพื่อวนค่า)")
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def _place_initial(self):
        mon = self.api.primary_monitor() if self.api else None
        if mon:
            wx, wy, ww, wh = mon.work
        else:
            wx, wy = 0, 0
            ww, wh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.update_idletasks()
        w = self.root.winfo_reqwidth()
        h = self.root.winfo_reqheight()
        px = self.settings.get("panel_x")
        py = self.settings.get("panel_y")
        if not isinstance(px, int) or not isinstance(py, int):
            px = wx + max(0, (ww - w) // 2)
            py = max(wy, wy + wh - h - 6)
        px = max(wx - w + 80, min(px, wx + ww - 80))
        py = max(wy, min(py, wy + wh - 40))
        self.root.geometry(f"{w}x{h}+{int(px)}+{int(py)}")

    # ================= ลูปหลัก / คิว =================
    def run(self):
        self.refresh_list(force=True)
        self.hotkeys.start()
        self.drag.start()
        self._pump()
        self._poll_active()
        self.root.mainloop()

    def _pump(self):
        for _ in range(200):
            try:
                fn = self.cmd_q.get_nowait()
            except queue.Empty:
                break
            try:
                fn()
            except Exception:
                pass
        try:
            self.root.after(60, self._pump)
        except Exception:
            pass  # หน้าต่างถูกปิดแล้ว

    def _poll_active(self):
        try:
            fg = self.api.foreground_hwnd() if self.api else None
            if fg != self._last_fg:
                self._last_fg = fg
                for hwnd, row in self._rows.items():
                    active = (hwnd == fg)
                    bg = COLORS["row_active"] if active else COLORS["row"]
                    row["frame"].configure(bg=bg)
                    row["label"].configure(bg=bg,
                                           fg=COLORS["fg"] if active else COLORS["muted"])
                    row["min"].configure(bg=bg)
                    row["max"].configure(bg=bg)
                    row["close"].configure(bg=bg)
        except Exception:
            pass
        try:
            self.root.after(900, self._poll_active)
        except Exception:
            pass

    # ================= รายการหน้าต่าง =================
    def refresh_list(self, force=False):
        try:
            wins = self.api.enumerate_windows() if self.api else []
            self._windows = wins
            f = self._filter.strip().lower()
            shown = [w for w in wins if f in w.title.lower()] if f else wins
            sig = tuple((w.hwnd, w.title, w.minimized, w.is_maximized) for w in shown)
            if sig != self._row_sig or force:
                self._row_sig = sig
                self._rebuild(shown)
            # เก็บกวาดตำแหน่งเดิมของหน้าต่างที่ปิดไปแล้ว
            for hwnd in list(self.original_rects):
                if not self.api.is_window(hwnd):
                    del self.original_rects[hwnd]
        except Exception:
            pass
        try:
            self.root.after(1300, lambda: self.refresh_list())
        except Exception:
            pass

    def _rebuild(self, shown):
        for child in self.inner.winfo_children():
            child.destroy()
        self._rows = {}
        c = COLORS
        if not shown:
            self.empty_lbl = tk.Label(self.inner, text="ไม่พบหน้าต่างโปรแกรม",
                                      bg=c["bg"], fg=c["muted"], font=ui_font(10),
                                      pady=30, padx=self.PANEL_W // 2 - 80)
            self.empty_lbl.pack(fill="x", padx=10, pady=10)
            return
        for w in shown:
            self._build_row(w)

    def _build_row(self, w):
        c = COLORS
        row = tk.Frame(self.inner, bg=c["row"], padx=4, pady=3)
        row.pack(fill="x", padx=6, pady=2)

        title = w.title if len(w.title) <= 46 else w.title[:45] + "…"
        state = " (ย่ออยู่)" if w.minimized else (" (เต็มจอ)" if w.is_maximized else "")
        lbl = tk.Label(row, text=f"  {title}{state}", anchor="w", bg=c["row"],
                       fg=c["muted"], font=ui_font(10), padx=4)
        lbl.pack(side="left", fill="x", expand=True)

        btn_close = self._make_icon(row, "✕", c["danger"],
                                    lambda h=w.hwnd: self._act_close(h))
        btn_max = self._make_icon(row, "▢", c["fg"],
                                  lambda h=w.hwnd: self._act_toggle_max(h))
        btn_min = self._make_icon(row, "–", c["fg"],
                                  lambda h=w.hwnd: self._act_minimize(h))
        lbl.bind("<Button-1>", lambda e, h=w.hwnd: self._act_focus(h))
        self._hover(lbl, c["fg"])

        self._rows[w.hwnd] = {"frame": row, "label": lbl,
                              "min": btn_min, "max": btn_max, "close": btn_close}

    # ================= อินพุต UI =================
    def _header_press(self, event):
        self._drag_off = (event.x, event.y)

    def _header_drag(self, event):
        x = self.root.winfo_x() + event.x - self._drag_off[0]
        y = self.root.winfo_y() + event.y - self._drag_off[1]
        self.root.geometry(f"+{int(x)}+{int(y)}")

    def _header_release(self, _event):
        self.settings["panel_x"] = int(self.root.winfo_x())
        self.settings["panel_y"] = int(self.root.winfo_y())
        save_settings(self.settings, self.settings_path)

    def _search_focus_in(self, _e):
        if not self._filter and self.search_entry.get().startswith("ค้นหา"):
            self.search_entry.delete(0, "end")
            self.search_entry.configure(fg=COLORS["fg"])

    def _search_focus_out(self, _e):
        if not self.search_entry.get():
            self.search_entry.insert(0, "ค้นหาหน้าต่าง…")
            self.search_entry.configure(fg=COLORS["muted"])

    def _on_search(self, *_args):
        self._filter = self.search_var.get()
        if self._filter.startswith("ค้นหา"):
            self._filter = ""
        self.refresh_list(force=True)

    # ================= การกระทำต่อหน้าต่าง =================
    def _act_focus(self, hwnd):
        if self.api:
            self.api.force_foreground(hwnd)

    def _act_minimize(self, hwnd):
        if self.api:
            self.api.show_window(hwnd, SW_MINIMIZE)
            self.root.after(150, lambda: self.refresh_list(force=True))

    def _act_toggle_max(self, hwnd):
        if not self.api:
            return
        if self.api.user32.IsZoomed(hwnd):
            self.api.show_window(hwnd, SW_RESTORE)
        else:
            self.api.show_window(hwnd, SW_MAXIMIZE)
        self.root.after(150, lambda: self.refresh_list(force=True))

    def _act_close(self, hwnd):
        if self.api:
            self.api.close_window(hwnd)
            self.root.after(250, lambda: self.refresh_list(force=True))

    def minimize_all(self):
        if not self.api:
            return
        for w in self.api.enumerate_windows():
            try:
                self.api.show_window(w.hwnd, SW_MINIMIZE)
            except Exception:
                pass
        self._toast_active_monitor("ย่อทุกหน้าต่างแล้ว")

    # ================= สแนปเข้าโซน =================
    def snap_window_to_zone(self, hwnd, idx, monitor=None, layout_key=None):
        """สแนปหน้าต่างเข้าโซน idx (0-based) — กดซ้ำที่โซนเดิม = คืนตำแหน่งเดิม"""
        if not self.api:
            return False
        if not self.api.is_window(hwnd) or self.api.is_our_window(hwnd):
            return False
        mon = monitor or self.api.monitor_from_window(hwnd)
        if not mon:
            return False
        key = layout_key or self.settings.get("layout", "halves")
        fractions = LAYOUTS.get(key, LAYOUTS["halves"])["zones"]
        gap = int(self.settings.get("gap_px", 8))
        rects = compute_zone_rects(mon.work, fractions, gap)
        if idx < 0 or idx >= len(rects):
            return False
        rect = rects[idx]
        cur = self.api.window_rect(hwnd)
        if cur and window_occupies_zone(cur, rect):
            return self.restore_original(hwnd)
        if hwnd not in self.original_rects:
            orig = self.api.normal_rect(hwnd)
            if orig and (orig[2] - orig[0]) > 120 and (orig[3] - orig[1]) > 120:
                self.original_rects[hwnd] = orig
        x, y, w, h = rect
        self.api.snap_window(hwnd, x, y, w, h)
        return True

    def restore_original(self, hwnd):
        rect = self.original_rects.get(hwnd)
        if not rect:
            return False
        try:
            self.api.move_window(hwnd, rect)
            self.api.force_foreground(hwnd)
        except Exception:
            pass
        self.original_rects.pop(hwnd, None)
        return True

    def unsnap_active(self):
        if not self.api:
            return
        hwnd = self.api.foreground_hwnd()
        if not hwnd or self.api.is_our_window(hwnd):
            return
        if not self.restore_original(hwnd):
            self._toast_active_monitor("ไม่มีตำแหน่งเดิมบันทึกไว้")

    def _drag_snap_apply(self, hwnd, idx, mon):
        self.snap_window_to_zone(hwnd, idx, monitor=mon)

    def snap_active_zone(self, idx, layout_key=None):
        """สแนปหน้าต่างที่กำลังใช้งานเข้าโซน idx — ใช้กับ Ctrl+Alt+1-9 / ←/→"""
        if not self.api:
            return
        hwnd = self.api.foreground_hwnd()
        if not hwnd or self.api.is_our_window(hwnd):
            return
        if not self.snap_window_to_zone(hwnd, idx, layout_key=layout_key):
            if layout_key is None:
                # กดเลขเกินจำนวนโซนของเลย์เอาต์ — แจ้งเบา ๆ
                n = len(LAYOUTS.get(self.settings["layout"], {}).get("zones", []))
                if idx + 1 > n:
                    self._toast_active_monitor(
                        f"เลย์เอาต์นี้มี {n} โซน — ไม่มีโซน {idx + 1}")

    def maximize_active(self):
        if not self.api:
            return
        hwnd = self.api.foreground_hwnd()
        if hwnd and not self.api.is_our_window(hwnd):
            self.api.show_window(hwnd, SW_MAXIMIZE)

    def minimize_active(self):
        if not self.api:
            return
        hwnd = self.api.foreground_hwnd()
        if hwnd and not self.api.is_our_window(hwnd):
            self.api.show_window(hwnd, SW_MINIMIZE)

    # ================= เลย์เอาต์ / การตั้งค่า =================
    def set_layout(self, key):
        if key not in LAYOUTS:
            return
        self.settings["layout"] = key
        save_settings(self.settings, self.settings_path)
        self._update_layout_button()
        self._toast_active_monitor(f"เลย์เอาต์: {LAYOUTS[key]['name']}")

    def cycle_layout(self):
        idx = LAYOUT_ORDER.index(self.settings["layout"])
        self.set_layout(LAYOUT_ORDER[(idx + 1) % len(LAYOUT_ORDER)])

    def toggle_drag_snap(self):
        self.settings["drag_snap"] = not self.settings.get("drag_snap", True)
        save_settings(self.settings, self.settings_path)
        self._toast_active_monitor(
            "ลากหน้าต่างเข้าโซน: " + ("เปิด" if self.settings["drag_snap"] else "ปิด"))

    def cycle_gap(self):
        cur = int(self.settings.get("gap_px", 8))
        self.settings["gap_px"] = GAP_CHOICES[(GAP_CHOICES.index(cur) + 1) % len(GAP_CHOICES)]
        save_settings(self.settings, self.settings_path)
        self._toast_active_monitor(f"ระยะเว้นโซน: {self.settings['gap_px']}px")

    def _update_layout_button(self):
        name = LAYOUTS[self.settings["layout"]]["name"]
        self.layout_btn.configure(text=f"{name} ▸")

    def _toast_active_monitor(self, text):
        mon = None
        if self.api:
            hwnd = self.api.foreground_hwnd()
            if hwnd:
                mon = self.api.monitor_from_window(hwnd)
            mon = mon or self.api.primary_monitor()
        if mon:
            self.overlay.show_toast(mon, text)

    # ================= overlay / แถบ =================
    def toggle_overlay(self):
        if self.overlay.visible():
            self.overlay.hide()
            return
        target = self.api.foreground_hwnd() if self.api else None
        if target and self.api.is_our_window(target):
            target = None
        if not target and self._windows:
            # ไม่มีหน้าต่างที่ใช้งานอยู่ (โฟกัสอยู่ที่เดสก์ท็อป) — ใช้หน้าต่างบนสุดแทน
            target = self._windows[0].hwnd
        mon = None
        if target:
            mon = self.api.monitor_from_window(target)
        mon = mon or (self.api.primary_monitor() if self.api else None)
        if mon:
            self.overlay.show_manual(mon, target)

    def hide_panel(self):
        self.root.withdraw()
        self._show_tab()

    def show_panel(self):
        if self.tab and self.tab.winfo_exists():
            self.tab.withdraw()
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.refresh_list(force=True)

    def toggle_panel(self):
        if self.root.state() == "withdrawn":
            self.show_panel()
        else:
            self.hide_panel()

    def _show_tab(self):
        if self.tab and self.tab.winfo_exists():
            self.tab.deiconify()
            return
        tab = tk.Toplevel(self.root)
        tab.title(APP_TITLE_PREFIX + "-Tab")
        tab.overrideredirect(True)
        tab.attributes("-topmost", True)
        tab.configure(bg=COLORS["accent"])
        btn = tk.Label(tab, text=" ⊞ หน้าต่าง ", bg=COLORS["accent"], fg="#0b0c10",
                       font=ui_font(9, True), padx=8, pady=5, cursor="hand2")
        btn.pack()
        btn.bind("<Button-1>", lambda e: self.show_panel())
        mon = self.api.primary_monitor() if self.api else None
        tab.update_idletasks()
        w, h = tab.winfo_reqwidth(), tab.winfo_reqheight()
        if mon:
            wx, wy, ww, wh = mon.work
            tab.geometry(f"{w}x{h}+{wx + ww - w - 8}+{wy + wh - h - 4}")
        else:
            tab.geometry(f"{w}x{h}+20+20")
        self.tab = tab

    # ================= ฮอตคีย์ / สถานะ =================
    def _hotkeys_ready(self, failed):
        self.failed_hotkeys = failed
        if failed:
            names = ", ".join(h.label.split(" — ")[0] for h in failed)
            self.status_lbl.configure(
                text=f"⚠ ฮอตคีย์ที่ลงทะเบียนไม่สำเร็จ (แอปอื่นใช้อยู่): {names}",
                fg=COLORS["danger"])

    def _set_default_status(self):
        self.status_lbl.configure(
            text="Ctrl+Alt+Z ผังโซน • Ctrl+Alt+←/→ ครึ่งจอ • Ctrl+Alt+0 คืนเดิม • "
                 "Ctrl+Alt+S ซ่อนแถบ • คลิกขวา = เมนู", fg=COLORS["muted"])

    def _dispatch_hotkey(self, name, extra):
        try:
            if name == "toggle_overlay":
                self.toggle_overlay()
            elif name == "snap_left":
                self.snap_active_zone(0, layout_key="halves")
            elif name == "snap_right":
                self.snap_active_zone(1, layout_key="halves")
            elif name == "maximize":
                self.maximize_active()
            elif name == "minimize":
                self.minimize_active()
            elif name == "unsnap":
                self.unsnap_active()
            elif name == "cycle_layout":
                self.cycle_layout()
            elif name == "toggle_panel":
                self.toggle_panel()
            elif name == "minimize_all":
                self.minimize_all()
            elif name == "quit":
                self.quit_app()
            elif name == "zone":
                self.snap_active_zone(int(extra) - 1)
        except Exception as e:
            try:
                self.status_lbl.configure(text=f"ผิดพลาด: {e}", fg=COLORS["danger"])
            except Exception:
                pass

    def quit_app(self):
        try:
            self.settings["panel_x"] = int(self.root.winfo_x())
            self.settings["panel_y"] = int(self.root.winfo_y())
        except Exception:
            pass
        save_settings(self.settings, self.settings_path)
        try:
            self.drag.stop()
        except Exception:
            pass
        try:
            self.hotkeys.stop()
            self.hotkeys.join(timeout=1.0)
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# จุดเริ่มโปรแกรม
# ---------------------------------------------------------------------------

def print_check():
    """โหมดตรวจสอบ (ใช้ได้ทุก OS รวม Linux) — พิมพ์เลย์เอาต์และการคำนวณโซน"""
    print("Kuroya Window Manager — check")
    print(f"settings file : {settings_path()}")
    print(f"platform      : {os.name} (Windows required: {'yes' if IS_WINDOWS else 'NO'})")
    print(f"tkinter       : {'OK' if tk else 'NOT INSTALLED (ต้องมีเพื่อรันจริงบน Windows)'}")
    sample_work = (0, 0, 1920, 1040)
    ok = True
    for key in LAYOUT_ORDER:
        lay = LAYOUTS[key]
        rects = compute_zone_rects(sample_work, lay["zones"], 8)
        # ตรวจว่าทุกโซนอยู่ในพื้นที่ทำงานและจุดกึ่งกลางโซนชี้ได้ถูกโซน
        for i, (x, y, w, h) in enumerate(rects):
            if zone_index_at(x + w // 2, y + h // 2, rects) != i:
                ok = False
                print(f"  !! โซน {i + 1} ของ {key} ชี้กลับได้โซนผิด")
        print(f"  {key:<10} {lay['name']:<16} {len(rects)} โซน -> {rects}")
    print(f"zone geometry : {'OK' if ok else 'FAILED'}")
    return 0 if ok else 1


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    if "--check" in argv:
        return print_check()
    if not IS_WINDOWS:
        print("โปรแกรมนี้ต้องรันบน Windows เท่านั้น (เรียกใช้ Win32 API ผ่าน ctypes)")
        print("ลอง: python window_manager.py --check   เพื่อดูเลย์เอาต์โซนได้ทุกแพลตฟอร์ม")
        return 1
    if tk is None:
        print("ไม่พบ tkinter — โปรดติดตั้ง Python จาก python.org แบบเต็ม (มี tkinter ให้ครับ)")
        return 1
    try:
        api = WinAPI()
    except Exception as e:
        print(f"โหลด Win32 API ไม่สำเร็จ: {e}")
        return 1
    if not api.try_acquire_mutex():
        print("Kuroya Window Manager กำลังรันอยู่แล้วในระบบนี้")
        return 1
    app = PanelApp(api)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
