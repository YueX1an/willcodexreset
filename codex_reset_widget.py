"""Tkinter floating card showing Codex reset probabilities.

Glass: software frosted glass — grab the desktop strip behind the window, blur it
with Pillow, and paint it as the card background. (Windows 10's DWM acrylic
cannot blur a Tk window, so we blur it ourselves.)

Runs DPI-aware so text renders crisply at the display's native resolution, lives
in the notification area (tray) instead of the taskbar.
"""
from __future__ import annotations

import ctypes
import os
import tkinter as tk
from datetime import datetime

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageGrab, ImageStat, ImageTk

import codex_reset_data as D


def _enable_dpi_awareness() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor DPI aware
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


_enable_dpi_awareness()


def _dpi_scale() -> float:
    """Physical pixels per 96-DPI logical pixel."""
    try:
        return ctypes.windll.user32.GetDpiForSystem() / 96.0
    except Exception:
        return 1.0


S = _dpi_scale()


def _s(v: float) -> int:
    return int(round(v * S))


# ---- 尺寸（逻辑像素 × S = 物理像素）----
W, H = _s(320), _s(200)
RADIUS = _s(24)

# ---- 浅色玻璃（iOS 淡灰）----
GLASS = os.environ.get("CODEX_WIDGET_GLASS", "software")
ALPHA = float(os.environ.get("CODEX_WIDGET_ALPHA", "0.86"))
BLUR = int(os.environ.get("CODEX_WIDGET_BLUR", "20"))
TINT = float(os.environ.get("CODEX_WIDGET_TINT", "0.12"))
SAT = float(os.environ.get("CODEX_WIDGET_SAT", "1.12"))
TINT_RGB = (245, 248, 255)
BG = "#DDE6F0"
FG = "#1C1C1E"
DIM = "#525E6B"
ACCENT = "#245C9C"
PIN_ON = ACCENT

REFRESH_MS = 600_000  # 10 分钟

F_TITLE = ("Segoe UI", -_s(12), "bold")
F_LABEL = ("Segoe UI", -_s(12))
F_BIG = ("Segoe UI", -_s(28), "bold")
F_VERDICT = ("Segoe UI", -_s(16), "bold")
F_BODY = ("Segoe UI", -_s(12))
F_FOOT = ("Segoe UI", -_s(11))


def _round_region(hwnd: int, w: int, h: int, r: int) -> None:
    rgn = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, w + 1, h + 1, r, r)
    ctypes.windll.user32.SetWindowRgn(int(hwnd), rgn, True)


def _hide_from_taskbar(hwnd: int) -> None:
    GWL_EXSTYLE = -20
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_APPWINDOW = 0x00040000
    GA_ROOT = 2
    SWP_FRAMECHANGED = 0x0020
    SWP_NOACTIVATE = 0x0010
    SWP_NOZORDER = 0x0004
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    user32 = ctypes.windll.user32
    # Tk's winfo_id() is the child drawing window; Explorer sees its wrapper.
    wrapper = user32.GetAncestor(int(hwnd), GA_ROOT) or int(hwnd)
    ex = user32.GetWindowLongW(wrapper, GWL_EXSTYLE)
    user32.SetWindowLongW(wrapper, GWL_EXSTYLE, (ex | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW)
    user32.SetWindowPos(wrapper, 0, 0, 0, 0, 0,
                        SWP_FRAMECHANGED | SWP_NOACTIVATE | SWP_NOZORDER | SWP_NOMOVE | SWP_NOSIZE)


def _tray_image() -> Image.Image:
    n = 64
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([4, 4, n - 4, n - 4], radius=15, fill=(0, 122, 255, 255))
    d.ellipse([21, 21, 43, 43], fill=(255, 255, 255, 255))
    return img


def render_glass(source: Image.Image, size: tuple[int, int], blur: int = BLUR) -> Image.Image:
    """Make a legible, translucent glass surface from the desktop behind the card."""
    width, height = size
    base = source.convert("RGB").resize(size, Image.Resampling.LANCZOS)
    base = base.filter(ImageFilter.GaussianBlur(max(0, blur)))
    base = ImageEnhance.Color(base).enhance(SAT)
    luminance = ImageStat.Stat(base.convert("L")).mean[0]
    # Dark wallpapers need a little more milky tint for dark foreground text.
    tint = min(0.52, max(TINT, 0.65 - luminance / 320))
    glass = Image.blend(base, Image.new("RGB", size, TINT_RGB), tint).convert("RGBA")

    sheen = Image.new("RGBA", size)
    sheen_pixels = ImageDraw.Draw(sheen)
    for y in range(height):
        fraction = y / max(1, height - 1)
        opacity = round(37 * (1 - fraction) ** 2 + 5)
        sheen_pixels.line((0, y, width, y), fill=(255, 255, 255, opacity))
    glass = Image.alpha_composite(glass, sheen)

    return glass.convert("RGB")


class Widget:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Codex Reset")
        self.root.overrideredirect(True)
        self.root.geometry(f"{W}x{H}+{self.root.winfo_screenwidth() - W - _s(40)}+{_s(60)}")
        self.root.configure(bg=BG)
        self._drag = None
        self._pinned = False
        self._hidden = False
        self._bg_photo = None
        self.tray = None
        self._build()
        self.root.update_idletasks()
        self._apply_glass()
        _hide_from_taskbar(self.root.winfo_id())
        self._bind_events()
        self.refresh()
        self.root.after(200, self._update_background)
        self._start_tray()

    # ---- 玻璃 ----
    def _apply_glass(self) -> None:
        hwnd = self.root.winfo_id()
        try:
            self.root.attributes("-alpha", ALPHA if GLASS == "alpha" else 1.0)
            _round_region(hwnd, W, H, RADIUS)
        except Exception as exc:
            print(f"glass unavailable, falling back to translucent: {exc}")
            self.root.attributes("-alpha", ALPHA)

    def _update_background(self) -> None:
        if GLASS != "software" or self._hidden:
            return
        x, y = self.root.winfo_x(), self.root.winfo_y()
        # Per-monitor DPI awareness already makes Tk geometry physical pixels.
        box = (x, y, x + W, y + H)
        self.root.withdraw()
        self.root.update_idletasks()
        try:
            shot = ImageGrab.grab(bbox=box, all_screens=True).convert("RGB")
        except Exception as exc:
            print(f"background grab failed: {exc}")
            shot = None
        finally:
            self.root.deiconify()
            try:
                _round_region(self.root.winfo_id(), W, H, RADIUS)
            except Exception:
                pass
        if shot is None:
            shot = Image.new("RGB", (W, H), BG)
        out = render_glass(shot, (W, H))
        self._bg_photo = ImageTk.PhotoImage(out)
        self.canvas.itemconfigure(self.bg_item, image=self._bg_photo)

    # ---- 布局 ----
    def _build(self) -> None:
        self.canvas = tk.Canvas(self.root, width=W, height=H, bg=BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        c = self.canvas
        self.bg_item = c.create_image(0, 0, anchor="nw")
        c.create_line(_s(18), _s(176), W - _s(18), _s(176), fill="#9DAFC0")
        # 标题行
        self.t_title = c.create_text(_s(18), _s(24), text="CODEX RESET", anchor="w", fill=ACCENT, font=F_TITLE)
        self.t_dot = c.create_oval(_s(190), _s(20), _s(198), _s(28), fill=D.GREEN, outline="")
        self.t_status = c.create_text(_s(202), _s(24), text="实时", anchor="w", fill=DIM, font=F_BODY)
        # 置顶图钉：无底框，右上角保留足够大的点击区域。
        x, y = _s(290), _s(23)
        self.pin_head = c.create_polygon(
            x - _s(6), y - _s(7), x + _s(6), y - _s(7),
            x + _s(5), y - _s(3), x + _s(3), y - _s(3),
            x + _s(2), y + _s(3), x - _s(2), y + _s(3),
            x - _s(3), y - _s(3), x - _s(5), y - _s(3),
            fill=DIM, outline="", tags="pin",
        )
        self.pin_stem = c.create_line(x, y + _s(3), x, y + _s(10), fill=DIM, width=max(1, _s(1.5)), tags="pin")
        # 概率
        c.create_text(_s(18), _s(60), text="24h", anchor="w", fill=DIM, font=F_LABEL)
        self.t_p24 = c.create_text(_s(62), _s(60), text="--", anchor="w", font=F_BIG)
        c.create_text(_s(182), _s(60), text="48h", anchor="w", fill=DIM, font=F_LABEL)
        self.t_p48 = c.create_text(_s(226), _s(60), text="--", anchor="w", font=F_BIG)
        # 状态词
        self.t_verdict = c.create_text(_s(18), _s(100), text="—", anchor="w", font=F_VERDICT)
        # 上次重置
        c.create_text(_s(18), _s(132), text="上次重置", anchor="w", fill=DIM, font=F_LABEL)
        self.t_last = c.create_text(_s(96), _s(132), text="—", anchor="w", fill=FG, font=F_BODY)
        # 预告
        self.t_prev_label = c.create_text(_s(18), _s(156), text="预告", anchor="w", fill=DIM, font=F_LABEL)
        self.t_prev = c.create_text(_s(96), _s(156), text="", anchor="w", fill=FG, font=F_BODY)
        # 页脚（居中）
        self.t_foot = c.create_text(W // 2, _s(189), text="", anchor="center", fill=DIM, font=F_FOOT)

    # ---- 交互 ----
    def _bind_events(self) -> None:
        for w in (self.root, self.canvas):
            w.bind("<Button-1>", self._on_press)
            w.bind("<B1-Motion>", self._on_drag)
            w.bind("<ButtonRelease-1>", self._on_release)
            w.bind("<Double-Button-1>", lambda e: self.refresh())
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="隐藏到托盘", command=self._toggle_show)
        menu.add_command(label="置顶/取消置顶", command=self._toggle_pin)
        menu.add_command(label="立即刷新", command=self.refresh)
        menu.add_command(label="退出", command=self._quit)
        for w in (self.root, self.canvas):
            w.bind("<Button-3>", lambda e, m=menu: m.tk_popup(e.x_root, e.y_root))

    def _toggle_pin(self, _event=None):
        self._pinned = not self._pinned
        self.root.attributes("-topmost", self._pinned)
        color = PIN_ON if self._pinned else DIM
        self.canvas.itemconfigure(self.pin_head, fill=color)
        self.canvas.itemconfigure(self.pin_stem, fill=color)

    def _on_press(self, e):
        if e.widget is self.canvas and _s(267) <= e.x <= _s(312) and _s(8) <= e.y <= _s(42):
            self._drag = None
            self._toggle_pin()
            return "break"
        self._drag = (e.x, e.y)

    def _on_drag(self, e):
        if not self._drag:
            return
        self.root.geometry(f"+{self.root.winfo_x() + e.x - self._drag[0]}+{self.root.winfo_y() + e.y - self._drag[1]}")

    def _on_release(self, _e):
        if self._drag:
            self._drag = None
            self.root.after(60, self._update_background)

    # ---- 托盘 ----
    def _start_tray(self) -> None:
        try:
            import pystray
        except Exception as exc:
            print(f"tray unavailable: {exc}")
            return
        menu = pystray.Menu(
            pystray.MenuItem("显示 / 隐藏", self._toggle_show, default=True),
            pystray.MenuItem("置顶 / 取消置顶", lambda *a: self.root.after(0, self._toggle_pin)),
            pystray.MenuItem("立即刷新", lambda *a: self.root.after(0, self.refresh)),
            pystray.MenuItem("退出", lambda *a: self.root.after(0, self._quit)),
        )
        self.tray = pystray.Icon("codex_reset", _tray_image(), "Codex Reset", menu)
        try:
            self.tray.run_detached()
        except Exception as exc:
            print(f"tray failed: {exc}")

    def _toggle_show(self, *a):
        def f():
            if self._hidden:
                self.root.deiconify()
                self._hidden = False
                self.root.after(60, self._update_background)
            else:
                self.root.withdraw()
                self._hidden = True
        self.root.after(0, f)

    def _quit(self, *a):
        try:
            if self.tray:
                self.tray.stop()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    # ---- 刷新 ----
    def _truncate(self, s: str, n: int = 30) -> str:
        return s if len(s) <= n else s[: n - 1] + "…"

    def _set_row(self, prev_label, prev_text) -> None:
        if prev_text:
            self.canvas.itemconfigure(self.t_prev_label, text=prev_label)
            self.canvas.itemconfigure(self.t_prev, text=self._truncate(prev_text), state="normal")
        else:
            self.canvas.itemconfigure(self.t_prev_label, text="")
            self.canvas.itemconfigure(self.t_prev, text="")

    def refresh(self) -> None:
        try:
            data = D.extract_data(D.fetch_raw())
            vm = D.derive_view(data, datetime.now().astimezone().tzinfo)
            c = self.canvas
            c.itemconfigure(self.t_p24, text=f"{vm['prob24h']}%", fill=vm["prob24h_color"])
            c.itemconfigure(self.t_p48, text=f"{vm['prob48h']}%", fill=vm["prob48h_color"])
            c.itemconfigure(self.t_verdict, text=vm["verdict"], fill=vm["verdict_color"])
            if vm["last_reset_date"]:
                c.itemconfigure(self.t_last, text=f"{vm['last_reset_date']}（{vm['last_reset_days']}天前）")
            else:
                c.itemconfigure(self.t_last, text="—")
            self._set_row("预告", vm["preview"])
            c.itemconfigure(self.t_foot, text=f"更新 {vm['updated_hhmm']}", fill=DIM)
            c.itemconfigure(self.t_dot, fill=D.GREEN)
            c.itemconfigure(self.t_status, text="实时", fill=DIM)
        except Exception as exc:
            now = datetime.now().strftime("%H:%M")
            self.canvas.itemconfigure(self.t_dot, fill=D.ORANGE)
            self.canvas.itemconfigure(self.t_status, text="离线", fill=D.ORANGE)
            self.canvas.itemconfigure(self.t_foot, text=f"⚠ 更新失败 {now}", fill=D.ORANGE)
            print(f"refresh failed: {exc}")
        finally:
            self.root.after(REFRESH_MS, self.refresh)

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    Widget().run()
