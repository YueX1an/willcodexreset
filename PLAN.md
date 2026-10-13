# Codex Reset 桌面小组件 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Windows 桌面常驻一个 iOS 液态玻璃质感的悬浮卡片，每 10 分钟刷新并显示 Codex 重置概率、状态词、上次重置时间与负责人预告。

**Architecture:** 拆成"纯数据层"与"UI 层"两个文件。`codex_reset_data.py` 负责 HTTP 抓取、解析、派生视图模型（纯函数、可单测、不依赖网络）；`codex_reset_widget.py` 负责 Tkinter 渲染、Windows DWM 玻璃、拖拽与定时刷新。数据层先行并 TDD 覆盖，UI 层靠截图人工验证。

**Tech Stack:** Python 3.12（标准库 only：`urllib` / `json` / `datetime` / `tkinter` / `ctypes`），pytest 8.3（仅测试用）。

设计文档见 `DESIGN.md`。

---

## File Structure

- `codex_reset_data.py` — 创建。纯数据层：`fetch_raw` / `extract_data` / 配色函数 / 时间函数 / `derive_view`。
- `codex_reset_widget.py` — 创建。UI 层：Tkinter 悬浮卡片 + DWM 玻璃 + 拖拽 + 右键菜单 + 10 分钟刷新。
- `tests/test_codex_reset_data.py` — 创建。数据层单测（全部离线）。
- `codex_reset_widget.bat` — 创建。用 `pythonw` 启动的启动器。
- `.gitignore` — 创建。忽略 `__pycache__` 等。
- `README.md` — 修改。补一段使用说明。

**统一约定：**
- 解释器：`C:\Users\leozhang\anaconda3\envs\yt-dlp\python.exe`（下称 `$PY`），无窗口版 `pythonw.exe`。
- 仓库根：`E:\OneDrive\应用\willcodexreset\`（下称仓库根）。所有 git 命令用 `git -C "<仓库根>"`。
- 颜色用 iOS 系统色：绿 `#34C759`、橙 `#FF9F0A`、红 `#FF453A`、灰 `#8E8E93`。

---

### Task 1: 仓库脚手架

**Files:**
- Create: `.gitignore`
- Create: `tests/test_codex_reset_data.py`（先放一个占位测试，确认 pytest 能跑）

- [ ] **Step 1: 写 `.gitignore`**

```
__pycache__/
*.pyc
.pytest_cache/
*.log
```

- [ ] **Step 2: 写占位测试**

`tests/test_codex_reset_data.py`:
```python
def test_pytest_runs():
    assert True
```

- [ ] **Step 3: 运行确认 pytest 可跑**

Run: `C:\Users\leozhang\anaconda3\envs\yt-dlp\python.exe -m pytest tests -q`
（在仓库根执行）
Expected: `1 passed`

- [ ] **Step 4: 提交**

```bash
git -C "E:\OneDrive\应用\willcodexreset" add .gitignore tests/test_codex_reset_data.py
git -C "E:\OneDrive\应用\willcodexreset" commit -m "chore: scaffold tests and gitignore"
```

---

### Task 2: 数据层 — 抓取与解析

**Files:**
- Create: `codex_reset_data.py`
- Modify: `tests/test_codex_reset_data.py`

- [ ] **Step 1: 写失败测试**

把 `tests/test_codex_reset_data.py` 覆盖为：
```python
import io
import json
import urllib.request

import pytest

import codex_reset_data as D

SAMPLE = {
    "code": 0,
    "message": "ok",
    "data": {
        "updatedAt": "2026-10-13T04:53:51.024Z",
        "probability24h": 89,
        "probability48h": 99,
        "verdict": "elevated",
        "timeline": [
            {"time": "2026-10-07T03:00:00.000Z", "resetConfirmed": True},
            {"time": "2026-10-10T03:00:00.000Z", "resetConfirmed": False},
        ],
        "tiboRelevantPosts": [{"detail": "Global reset landing by EOD PST time. Enjoy"}],
    },
}


def test_extract_data_ok():
    assert D.extract_data(SAMPLE)["probability24h"] == 89


def test_extract_data_rejects_bad_payload():
    with pytest.raises(ValueError):
        D.extract_data({"code": 1, "data": None})
    with pytest.raises(ValueError):
        D.extract_data("not a dict")


def test_fetch_raw_parses_json(monkeypatch):
    class FakeResp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=None):
        return FakeResp(json.dumps(SAMPLE).encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert D.fetch_raw("http://example.invalid")["code"] == 0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `C:\Users\leozhang\anaconda3\envs\yt-dlp\python.exe -m pytest tests -q`
Expected: FAIL（`ModuleNotFoundError: No module named 'codex_reset_data'`）

- [ ] **Step 3: 写最小实现**

`codex_reset_data.py`:
```python
"""Pure data layer for the Codex Reset widget: fetch, parse, derive the view model."""
from __future__ import annotations

import json
import urllib.request

API_URL = "https://willcodexreset.com/api/reset-radar"

GREEN = "#34C759"
ORANGE = "#FF9F0A"
RED = "#FF453A"
GRAY = "#8E8E93"


def fetch_raw(url: str = API_URL, timeout: int = 10) -> dict:
    """GET the endpoint and return the parsed top-level JSON. Raises on any error."""
    req = urllib.request.Request(url, headers={"User-Agent": "codex-reset-widget/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
    return json.loads(body.decode("utf-8"))


def extract_data(payload: dict) -> dict:
    """Return payload['data'], or raise ValueError if the payload is not the expected shape."""
    if not isinstance(payload, dict) or payload.get("code") != 0 or not isinstance(payload.get("data"), dict):
        raise ValueError(f"unexpected payload: {str(payload)[:200]}")
    return payload["data"]
```

- [ ] **Step 4: 运行测试确认通过**

Run: `C:\Users\leozhang\anaconda3\envs\yt-dlp\python.exe -m pytest tests -q`
Expected: PASS（4 passed）

- [ ] **Step 5: 提交**

```bash
git -C "E:\OneDrive\应用\willcodexreset" add codex_reset_data.py tests/test_codex_reset_data.py
git -C "E:\OneDrive\应用\willcodexreset" commit -m "feat(data): fetch and parse reset-radar payload"
```

---

### Task 3: 数据层 — 配色、时间与视图模型

**Files:**
- Modify: `codex_reset_data.py`
- Modify: `tests/test_codex_reset_data.py`

- [ ] **Step 1: 追加失败测试**

在 `tests/test_codex_reset_data.py` 末尾追加：
```python
from datetime import datetime, timezone, timedelta

TZ8 = timezone(timedelta(hours=8))


def test_prob_color_thresholds():
    assert D.prob_color(10) == D.GREEN
    assert D.prob_color(29) == D.GREEN
    assert D.prob_color(30) == D.ORANGE
    assert D.prob_color(69) == D.ORANGE
    assert D.prob_color(70) == D.RED
    assert D.prob_color(99) == D.RED


def test_verdict_color_mapping():
    assert D.verdict_color("elevated") == D.RED
    assert D.verdict_color("moderate") == D.ORANGE
    assert D.verdict_color("low") == D.GREEN
    assert D.verdict_color("weird") == D.GRAY
    assert D.verdict_color("") == D.GRAY


def test_fmt_local_hhmm_converts_utc_to_tz():
    assert D.fmt_local_hhmm("2026-10-13T04:53:51.024Z", TZ8) == "12:53"


def test_days_since():
    now = datetime(2026, 10, 13, 12, 0, tzinfo=TZ8)
    assert D.days_since("2026-10-07T03:00:00.000Z", now) == 6


def test_last_confirmed_reset_picks_latest_and_none():
    assert D.last_confirmed_reset(SAMPLE["data"]["timeline"]) == "2026-10-07T03:00:00.000Z"
    assert D.last_confirmed_reset([]) is None
    assert D.last_confirmed_reset([{"time": "2026-10-10T00:00:00Z", "resetConfirmed": False}]) is None


def test_derive_view_full():
    now = datetime(2026, 10, 13, 12, 53, tzinfo=TZ8)
    vm = D.derive_view(SAMPLE["data"], TZ8, now=now)
    assert vm["prob24h"] == 89
    assert vm["prob48h"] == 99
    assert vm["verdict"] == "ELEVATED"
    assert vm["verdict_color"] == D.RED
    assert vm["prob24h_color"] == D.RED
    assert vm["last_reset_date"] == "2026-10-07"
    assert vm["last_reset_days"] == 6
    assert vm["preview"] == "Global reset landing by EOD PST time. Enjoy"
    assert vm["updated_hhmm"] == "12:53"


def test_derive_view_without_optional_fields():
    now = datetime(2026, 10, 13, 12, 0, tzinfo=TZ8)
    vm = D.derive_view({"probability24h": 5, "probability48h": 5, "updatedAt": "2026-10-13T04:00:00Z"}, TZ8, now=now)
    assert vm["preview"] is None
    assert vm["last_reset_date"] is None
    assert vm["last_reset_days"] is None
    assert vm["verdict"] == "—"
    assert vm["verdict_color"] == D.GRAY
    assert vm["prob24h_color"] == D.GREEN
```

- [ ] **Step 2: 运行测试确认失败**

Run: `C:\Users\leozhang\anaconda3\envs\yt-dlp\python.exe -m pytest tests -q`
Expected: FAIL（`AttributeError: module 'codex_reset_data' has no attribute 'prob_color'` 等）

- [ ] **Step 3: 追加实现**

在 `codex_reset_data.py` 末尾追加：
```python
from datetime import datetime, tzinfo


def prob_color(p: int) -> str:
    if p >= 70:
        return RED
    if p >= 30:
        return ORANGE
    return GREEN


def verdict_color(v: str) -> str:
    v = (v or "").lower()
    if v in ("elevated", "high", "severe"):
        return RED
    if v in ("moderate", "medium"):
        return ORANGE
    if v in ("low", "calm", "quiet"):
        return GREEN
    return GRAY


def _parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def fmt_local_hhmm(iso_utc: str, tz: tzinfo) -> str:
    return _parse_iso(iso_utc).astimezone(tz).strftime("%H:%M")


def days_since(iso_utc: str, now: datetime) -> int:
    return (now - _parse_iso(iso_utc)).days


def last_confirmed_reset(timeline: list) -> str | None:
    confirmed = [t for t in (timeline or []) if t.get("resetConfirmed") and t.get("time")]
    if not confirmed:
        return None
    return max(confirmed, key=lambda t: t["time"])["time"]


def derive_view(data: dict, tz: tzinfo, now: datetime | None = None) -> dict:
    """Turn raw API `data` into everything the UI needs to render."""
    now = now or datetime.now(tz)
    last = last_confirmed_reset(data.get("timeline"))
    posts = data.get("tiboRelevantPosts") or []
    p24 = int(data.get("probability24h", 0))
    p48 = int(data.get("probability48h", 0))
    verdict = (data.get("verdict") or "").strip()
    return {
        "prob24h": p24,
        "prob48h": p48,
        "prob24h_color": prob_color(p24),
        "prob48h_color": prob_color(p48),
        "verdict": verdict.upper() if verdict else "—",
        "verdict_color": verdict_color(verdict),
        "last_reset_date": _parse_iso(last).astimezone(tz).strftime("%Y-%m-%d") if last else None,
        "last_reset_days": days_since(last, now) if last else None,
        "preview": posts[0].get("detail") if posts else None,
        "updated_hhmm": fmt_local_hhmm(data["updatedAt"], tz) if data.get("updatedAt") else "--:--",
    }
```

- [ ] **Step 4: 运行测试确认通过**

Run: `C:\Users\leozhang\anaconda3\envs\yt-dlp\python.exe -m pytest tests -q`
Expected: PASS（11 passed）

- [ ] **Step 5: 提交**

```bash
git -C "E:\OneDrive\应用\willcodexreset" add codex_reset_data.py tests/test_codex_reset_data.py
git -C "E:\OneDrive\应用\willcodexreset" commit -m "feat(data): colors, time helpers, and view model"
```

---

### Task 4: UI 层 — 悬浮玻璃卡片

**Files:**
- Create: `codex_reset_widget.py`

> UI 无法单测，用**截图人工验证**。玻璃有两档实现，按截图结果择一（见 Step 5）。

- [ ] **Step 1: 写完整实现**

`codex_reset_widget.py`:
```python
"""Tkinter floating card showing Codex reset probabilities, with Windows DWM acrylic glass."""
from __future__ import annotations

import ctypes
import tkinter as tk
from datetime import datetime

import codex_reset_data as D

W, H = 320, 200
RADIUS = 18
BG = "#0E0E14"        # 玻璃底色（半透明深色）
FG = "#F5F5F7"        # 主文字
DIM = "#9A9AA2"       # 次级文字
LINE = "#3A3A44"      # 分隔线 / 描边
ACCENT = "#5B8DEF"    # 标题强调
REFRESH_MS = 600_000  # 10 分钟
MAGIC = "#010203"     # transparentcolor 魔色（仅玻璃档②用到）

F_TITLE = ("Segoe UI", 9, "bold")
F_LABEL = ("Segoe UI", 9)
F_BIG = ("Segoe UI", 20, "bold")
F_VERDICT = ("Segoe UI", 12, "bold")
F_BODY = ("Segoe UI", 9)
F_FOOT = ("Segoe UI", 8)


def _enable_acrylic(hwnd: int) -> None:
    """Blur whatever is behind the window (Windows 10 acrylic)."""
    class ACCENT_POLICY(ctypes.Structure):
        _fields_ = [
            ("AccentState", ctypes.c_int),
            ("AccentFlags", ctypes.c_int),
            ("GradientColor", ctypes.c_uint),
            ("AnimationId", ctypes.c_int),
        ]

    class WCAData(ctypes.Structure):
        _fields_ = [
            ("Attribute", ctypes.c_int),
            ("Data", ctypes.POINTER(ACCENT_POLICY)),
            ("SizeOfData", ctypes.c_size_t),
        ]

    ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
    WCA_ACCENT_POLICY = 19
    accent = ACCENT_POLICY()
    accent.AccentState = ACCENT_ENABLE_ACRYLICBLURBEHIND
    accent.AccentFlags = 0x20 | 0x40 | 0x80 | 0x100
    accent.GradientColor = 0xD20E0E14  # AABBGGRR: alpha 0xD2 tint over blur
    data = WCAData(WCA_ACCENT_POLICY, ctypes.pointer(accent), ctypes.sizeof(accent))
    ctypes.windll.user32.SetWindowCompositionAttribute(int(hwnd), ctypes.byref(data))


def _round_region(hwnd: int, w: int, h: int, r: int) -> None:
    """Clip the window to a rounded rectangle (Win10 has no DWM corner API)."""
    rgn = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, w + 1, h + 1, r, r)
    ctypes.windll.user32.SetWindowRgn(int(hwnd), rgn, True)


class Widget:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Codex Reset")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.geometry(f"{W}x{H}+{self.root.winfo_screenwidth() - W - 40}+60")
        self.root.configure(bg=BG)
        self._drag = (0, 0)
        self._last_color = ACCENT
        self._build()
        self.root.update_idletasks()
        self._apply_glass(use_magic=False)   # 档①：global alpha，拖拽稳；若截图无玻璃感再试档②
        self._bind_events()
        self.refresh()

    # ---- 玻璃 ----
    def _apply_glass(self, use_magic: bool) -> None:
        hwnd = self.root.winfo_id()
        try:
            if use_magic:
                self.root.attributes("-alpha", 1.0)
                self.root.wm_attributes("-transparentcolor", MAGIC)
                self.canvas.configure(bg=MAGIC)
                for item in self.canvas.find_all():
                    if self.canvas.type(item) == "rectangle" and self.canvas.itemcget(item, "fill") == BG:
                        self.canvas.itemconfigure(item, fill=MAGIC)
            else:
                self.root.attributes("-alpha", 0.93)
            _enable_acrylic(hwnd)
            _round_region(hwnd, W, H, RADIUS)
        except Exception as exc:  # 任意 DWM 调用失败都退回半透明
            print(f"glass unavailable, falling back to translucent: {exc}")
            self.root.attributes("-alpha", 0.93)
            self.root.wm_attributes("-transparentcolor", "")

    # ---- 布局 ----
    def _build(self) -> None:
        self.canvas = tk.Canvas(self.root, width=W, height=H, bg=BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        c = self.canvas
        # 圆角底 + 细高光描边（模拟玻璃边缘）
        self._round_rect(2, 2, W - 2, H - 2, RADIUS, fill=BG, outline=LINE)
        self.canvas.create_line(16, 176, W - 16, 176, fill=LINE)
        # 标题行
        self.t_dot = c.create_oval(W - 74, 20, W - 66, 28, fill=D.GREEN, outline="")
        self.t_status = c.create_text(W - 60, 24, text="实时", anchor="w", fill=DIM, font=F_BODY)
        self.t_title = c.create_text(18, 24, text="CODEX RESET RADAR", anchor="w", fill=ACCENT, font=F_TITLE)
        # 概率
        c.create_text(18, 60, text="24h", anchor="w", fill=DIM, font=F_LABEL)
        self.t_p24 = c.create_text(62, 60, text="--", anchor="w", font=F_BIG)
        c.create_text(182, 60, text="48h", anchor="w", fill=DIM, font=F_LABEL)
        self.t_p48 = c.create_text(226, 60, text="--", anchor="w", font=F_BIG)
        # 状态词
        self.t_verdict = c.create_text(18, 100, text="—", anchor="w", font=F_VERDICT)
        # 上次重置
        c.create_text(18, 132, text="上次重置", anchor="w", fill=DIM, font=F_LABEL)
        self.t_last = c.create_text(96, 132, text="—", anchor="w", fill=FG, font=F_BODY)
        # 预告
        self.t_prev_label = c.create_text(18, 156, text="预告", anchor="w", fill=DIM, font=F_LABEL)
        self.t_prev = c.create_text(96, 156, text="", anchor="w", fill=FG, font=F_BODY)
        # 页脚（居中）
        self.t_foot = c.create_text(W // 2, 189, text="", anchor="center", fill=DIM, font=F_FOOT)

    def _round_rect(self, x1, y1, x2, y2, r, **kw):
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
               x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return self.canvas.create_polygon(pts, smooth=True, **kw)

    # ---- 交互 ----
    def _bind_events(self) -> None:
        self.root.bind("<Button-1>", self._on_press)
        self.root.bind("<B1-Motion>", self._on_drag)
        self.root.bind("<Double-Button-1>", lambda e: self.refresh())
        self.canvas.bind("<Button-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<Double-Button-1>", lambda e: self.refresh())
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="立即刷新", command=self.refresh)
        menu.add_command(label="退出", command=self.root.destroy)
        for w in (self.root, self.canvas):
            w.bind("<Button-3>", lambda e, m=menu: m.tk_popup(e.x_root, e.y_root))

    def _on_press(self, e):
        self._drag = (e.x, e.y)

    def _on_drag(self, e):
        self.root.geometry(f"+{self.root.winfo_x() + e.x - self._drag[0]}+{self.root.winfo_y() + e.y - self._drag[1]}")

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
```

- [ ] **Step 2: 冒烟运行（不校验外观）**

Run: `C:\Users\leozhang\anaconda3\envs\yt-dlp\python.exe codex_reset_widget.py`
Expected: 卡片出现在屏幕右上角，约 5 秒内显示出 24h/48h 百分比与状态词；控制台无异常堆栈。
若无窗口或报错 → 按报错修（常见：`SetWindowCompositionAttribute` 缺失 → 走 fallback 分支，打印 "glass unavailable"）。

- [ ] **Step 3: 截图**

另开一个终端执行（PowerShell）：
```powershell
Add-Type -AssemblyName System.Windows.Forms,System.Drawing
$b = New-Object System.Drawing.Bitmap([System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width, [System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height)
$g = [System.Drawing.Graphics]::FromImage($b)
$g.CopyFromScreen(0,0,0,0,$b.Size)
$b.Save("E:\temp\codex_widget_shot.png")
```
然后 Read 该 PNG，检查：磨砂/半透明、圆角、文字与颜色、页脚"更新 HH:MM"**居中**。

- [ ] **Step 4: 断网降级验证**

把 `codex_reset_widget.py` 里 `D.fetch_raw()` 临时改成 `D.fetch_raw("http://127.0.0.1:1/x")`，重跑。
Expected: 状态点变橙、显示"离线"和"⚠ 更新失败 HH:MM"，程序不崩溃、窗口仍在。验证完**改回** `D.fetch_raw()`。

- [ ] **Step 5: 择玻璃档位**

看截图：若背景是真模糊（能看出后面桌面被虚化）→ 保持档①。若只是整体半透明、看不出模糊 → 把 `self._apply_glass(use_magic=False)` 改为 `self._apply_glass(use_magic=True)` 再跑再截图，对比是否更像磨砂玻璃、且**拖拽仍可用**（左键拖得动）。选外观更好且拖拽正常的那档，把选择写死进代码。

- [ ] **Step 6: 提交**

```bash
git -C "E:\OneDrive\应用\willcodexreset" add codex_reset_widget.py
git -C "E:\OneDrive\应用\willcodexreset" commit -m "feat(ui): floating acrylic glass card"
```

---

### Task 5: 启动器与开机自启

**Files:**
- Create: `codex_reset_widget.bat`

- [ ] **Step 1: 写启动器**

`codex_reset_widget.bat`:
```bat
@echo off
start "" "C:\Users\leozhang\anaconda3\envs\yt-dlp\pythonw.exe" "%~dp0codex_reset_widget.py"
```

- [ ] **Step 2: 验证双击能拉起**

双击 `codex_reset_widget.bat` → 卡片出现、无控制台黑框。
若已有一个实例在跑，先右键"退出"再双击，避免两个卡片。

- [ ] **Step 3: 建开机自启快捷方式**

PowerShell（生成指向 .bat 的快捷方式放进启动文件夹）：
```powershell
$startup = [Environment]::GetFolderPath('Startup')
$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut("$startup\Codex Reset Widget.lnk")
$lnk.TargetPath = "E:\OneDrive\应用\willcodexreset\codex_reset_widget.bat"
$lnk.WorkingDirectory = "E:\OneDrive\应用\willcodexreset"
$lnk.Save()
Get-Item "$startup\Codex Reset Widget.lnk" | Select-Object FullName
```
Expected: 打印出该 `.lnk` 路径即成功。（开机自启需重启才能端到端确认；无重启条件下，用"运行该 .lnk 能拉起卡片"作为等效证据。）

- [ ] **Step 4: 提交**

```bash
git -C "E:\OneDrive\应用\willcodexreset" add codex_reset_widget.bat
git -C "E:\OneDrive\应用\willcodexreset" commit -m "chore: add pythonw launcher"
```

---

### Task 6: 收尾 — README 与端到端复验

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 补 README**

`README.md`:
```markdown
# willcodexreset

A desktop widget for Windows showing live Codex reset probabilities from
[willcodexreset.com](https://willcodexreset.com/) — a floating frosted-glass card.

## Run

Double-click `codex_reset_widget.bat`, or:

    C:\Users\leozhang\anaconda3\envs\yt-dlp\pythonw.exe codex_reset_widget.py

Refreshes every 10 minutes; right-click the card for "立即刷新" / "退出";
double-click to refresh; drag to move. Auto-starts via a shortcut in
`shell:startup`.

## Data

`GET https://willcodexreset.com/api/reset-radar` — see `DESIGN.md`.

## Tests

    C:\Users\leozhang\anaconda3\envs\yt-dlp\python.exe -m pytest tests -q
```

- [ ] **Step 2: 端到端复验**

1. `python -m pytest tests -q` → 全绿
2. 退出旧实例，双击 `.bat` → 卡片出现
3. 卡片数值与 `curl -s https://willcodexreset.com/api/reset-radar` 的 `probability24h/48h`、`verdict` 一致
4. 拖拽移动、右键"立即刷新"/"退出"、双击刷新均生效
5. 页脚"更新 HH:MM"居中
6. 截图留档

- [ ] **Step 3: 提交并推送**

```bash
git -C "E:\OneDrive\应用\willcodexreset" add README.md
git -C "E:\OneDrive\应用\willcodexreset" commit -m "docs: usage and test instructions"
git -C "E:\OneDrive\应用\willcodexreset" push origin main
```

---

## Self-Review

- **Spec coverage**：数据源→Task2；配色/时间/派生→Task3；UI 布局与玻璃→Task4；10 分钟刷新与手动刷新→Task4（`REFRESH_MS=600_000`、菜单/双击）；页脚居中→Task4（`anchor="center"`，x=W//2）；容错降级→Task4 Step4；开机自启→Task5；验证方案→Task6。✅ 全覆盖。
- **Placeholder scan**：无 TBD/TODO；每个代码步骤都给了完整代码。✅
- **Type/命名一致性**：`derive_view` 返回键在 Task3 定义，Task4 使用的键（`prob24h`/`prob48h`/`prob24h_color`/`verdict`/`verdict_color`/`last_reset_date`/`last_reset_days`/`preview`/`updated_hhmm`）逐一对应。✅
