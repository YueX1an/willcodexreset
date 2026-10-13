# Codex Reset 桌面小组件 — 设计文档

日期：2026-10-13
状态：已确认，待实现

## 目标

在 Windows 桌面常驻一个 iOS 26 液态玻璃质感的悬浮小卡片，实时显示 Codex（OpenAI）重置概率与相关信息。

## 非目标

- 不做历史曲线图 / 事件流列表（网站已有，卡片只做"一眼看"）
- 不做声音/桌面通知告警
- 不做 Windows 11 小组件面板 / Rainmeter
- 不装第三方依赖（纯 Python 标准库）

## 数据源

- **接口**：`GET https://willcodexreset.com/api/reset-radar`（JSON，`Cache-Control: no-store`）
- **直连可用**（本机实测无需代理）；无 CORS 头，但本方案是 Python 端抓取，不受影响
- 响应结构：`{"code":0,"message":"ok","data":{...}}`

用到的字段：

| 字段 | 含义 | 用途 |
|---|---|---|
| `probability24h` / `probability48h` | 未来 24/48 小时重置概率（整数百分比）| 卡片主数字 |
| `verdict` | 状态词，如 `elevated` / `low` | 状态词 + 配色 |
| `timeline[].resetConfirmed` / `timeline[].time` | 已确认重置的标记与时间 | "上次重置" |
| `tiboRelevantPosts[0].detail` | 负责人最近的相关推文正文 | "预告"行 |
| `updatedAt` | 数据更新时间（ISO8601 UTC）| 页脚"更新"时间（本地时区显示 HH:MM）|

派生逻辑：
- **上次重置** = `timeline` 中 `resetConfirmed == true` 的最新一条的 `time`；显示日期 + 距今天数
- **预告** = `tiboRelevantPosts[0].detail`，按卡片宽度截断（超出加 `…`）；列表为空则隐藏该行
- **配色**：`verdict` → 颜色映射，`elevated`/`high` → 红，`moderate` → 橙，`low` → 绿，未知 → 灰
- **概率数字配色**（24h 各自判断）：`< 30` 绿，`30–69` 橙，`≥ 70` 红

## 界面

无边框、置顶、可拖动的玻璃卡片。

```
 ╭──────────────────────────────╮
 │ CODEX RESET RADAR      ● 实时 │
 │                               │
 │   24h  89%      48h  99%      │
 │   ELEVATED                    │
 │                               │
 │ 上次重置  2026-10-07 (6天前)   │
 │ 预告  Global reset landing    │
 │       by EOD PST time…        │
 │ ───────────────────────────── │
 │          更新 12:53           │   ← 居中
 ╰──────────────────────────────╯
```

- **默认尺寸**：约 320 × 200 px（可后续微调），不可缩放
- **状态点** `● 实时`：绿=本次抓取成功；黄=抓取失败（沿用上次数值）
- **主数字**：24h / 48h 概率，大号细体，按概率上色（越高越红）
- **状态词**：`verdict`，彩色
- **分隔线** 之上为数据区，之下为页脚
- **页脚**：`更新 HH:MM`，**水平居中**；不含"每N秒刷新"字样

## 视觉（iOS 26 液态玻璃）

用 Windows 原生 DWM，做**真实背景模糊**（非假透明）：

1. **磨砂**：`SetWindowCompositionAttribute` + `ACCENT_ENABLE_ACRYLICBLURBEHIND`，底色 `#0E0E14`、alpha ≈ 82%（`0xD2` 量级），使窗口背后的桌面真正被模糊
2. **圆角**：`CreateRoundRectRgn` + `SetWindowRgn` 裁出真圆角（半径 ~18px）——Win10 19045 无 DWM 圆角 API，用区域裁剪替代
3. **玻璃高光**：Canvas 绘 1px 淡白描边 + 顶部渐隐高光，模拟液态玻璃边缘折射
4. **字体**：Segoe UI；数字大号细体，正文近白 + 轻微阴影
5. **配色**：深色玻璃底 + verdict 强调色

**回退**：若 DWM 磨砂在该机上不生效（截图确认），退回 `-alpha 0.9` 的深色半透明面板（仍有玻璃观感，但不模糊背后）。

## 行为

- **启动即抓一次**
- **每 10 分钟自动刷新**（`root.after(600_000, ...)`）
- **手动刷新**：右键菜单"立即刷新" / 双击卡片
- **拖拽**：左键按住拖动移动窗口
- **退出**：右键菜单"退出"
- **容错**：抓取失败（超时 10s / 非 200 / JSON 解析失败）→ 保留上次数值，状态点转黄，页脚仍显示上次成功更新时间；不弹窗、不退出，等待下个周期
- **抓取方式**：`urllib.request`，`timeout=10`，直连

## 文件与自启

放在本项目仓库目录 `E:\OneDrive\应用\willcodexreset\`：

- `codex_reset_widget.py` — 主程序（纯标准库：`tkinter` / `urllib` / `json` / `ctypes` / `datetime`）
- `codex_reset_widget.bat` — 启动器，用 `pythonw.exe` 运行（无控制台黑框）
- `DESIGN.md` — 本设计文档
- 开机自启：把指向该 `.bat` 的快捷方式放入用户启动文件夹 `shell:startup`
- 远端仓库：`https://github.com/YueX1an/willcodexreset.git`

解释器：`C:\Users\leozhang\anaconda3\envs\yt-dlp\pythonw.exe`（已装 tkinter）。

## 验证方案

实现完成后，逐条**实测**（不靠断言）：

1. 运行 `pythonw codex_reset_widget.py`，**截屏**确认：卡片渲染、磨砂模糊、圆角、字段正确
2. 数值与 `curl https://willcodexreset.com/api/reset-radar` 的 `probability24h/48h`、`verdict` 比对一致
3. 断网（或改错 URL）跑一次 → 确认状态点转黄、保留旧值、不崩溃；恢复后自动回到正常
4. 拖拽移动、右键"立即刷新"/"退出"、双击刷新均生效
5. 双击 `.bat` 能拉起窗口；确认开机自启（放入 `shell:startup`）后重启可自动出现
6. 页脚"更新 HH:MM"确认居中

## 备注

- 项目仓库：`https://github.com/YueX1an/willcodexreset.git`（本地克隆 `E:\OneDrive\应用\willcodexreset\`）
