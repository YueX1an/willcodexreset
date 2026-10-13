# Codex Reset 桌面小组件

支持 **Windows 和 Mac**，显示 [willcodexreset.com](https://willcodexreset.com/) 的未来 24 / 48 小时重置概率、状态、上次确认重置时间和预告。

| 平台 | 形式 | 外观与使用 |
| --- | --- | --- |
| Windows | 桌面悬浮卡片 | 模拟磨砂背景，支持拖动、置顶和通知区域托盘 |
| Mac（macOS） | 原生 WidgetKit 桌面小组件 | 系统统一渲染背景和圆角，支持小、中、大三种尺寸 |

Mac 推荐使用 WidgetKit 版本，与天气、电池等系统小组件采用同一种外观机制。

## Windows 版本

### 安装与启动

需要 Windows、Python 3.10 或更新版本，以及可用的 Tkinter。安装两个运行依赖：

```powershell
python -m pip install Pillow pystray
```

在本目录运行：

```powershell
pythonw codex_reset_widget.py
```

`pythonw` 不显示控制台；排查启动或网络问题时，改用 `python codex_reset_widget.py` 查看错误输出。请使用安装了上述依赖的同一个 Python 环境。每次修改脚本后，先从托盘菜单退出旧实例，再重新启动。

### 使用

| 操作 | 效果 |
| --- | --- |
| 拖动卡片 | 移动位置，并重新采样该位置的桌面背景 |
| 点击右上角图钉 | 切换置顶；图钉变蓝表示已置顶 |
| 双击卡片 | 立即刷新数据 |
| 右键卡片 | 打开“隐藏到托盘、置顶/取消置顶、立即刷新、退出”菜单 |
| 点击通知区域的 Codex Reset 图标 | 显示或隐藏卡片 |

卡片默认每 10 分钟从 `https://willcodexreset.com/api/reset-radar` 刷新一次。抓取失败时会显示离线状态并等待下一次刷新。窗口不占任务栏位置；托盘图标位于 Windows 通知区域，是否收进 `^` 隐藏图标由 Windows 的任务栏设置决定。

磨砂背景在启动、拖动结束和从托盘重新显示时更新；桌面壁纸或其他窗口变化后，可以轻拖卡片让背景重新采样。

### 外观设置（Windows）

可以在启动前设置环境变量：

| 变量 | 默认值 | 作用 |
| --- | --- | --- |
| `CODEX_WIDGET_BLUR` | `20` | 背景模糊半径，越大越柔和 |
| `CODEX_WIDGET_TINT` | `0.12` | 浅色蒙层的最小混合比例，越小越透；深色背景会自动增加蒙层以保持文字可读 |
| `CODEX_WIDGET_SAT` | `1.12` | 背景颜色饱和度 |
| `CODEX_WIDGET_GLASS` | `software` | `software` 使用桌面截图生成模糊背景；`alpha` 使用普通窗口透明度 |
| `CODEX_WIDGET_ALPHA` | `0.86` | `alpha` 模式下的窗口不透明度 |

例如，想让背景更清晰：

```powershell
$env:CODEX_WIDGET_BLUR = '12'
pythonw codex_reset_widget.py
```

### 测试（Windows）

```powershell
python -m pip install pytest
python -m pytest tests -q
```

数据处理在 `codex_reset_data.py`，界面和托盘逻辑在 `codex_reset_widget.py`。

## Mac 版本（macOS）

`macos/widgetkit` 是真正的 WidgetKit 桌面小组件：背景、圆角、边框、尺寸和透明 / 着色外观由 macOS 渲染，与天气、电池等系统小组件使用同一种机制。支持小、中、大三种尺寸；推荐中号。

### 系统要求

- 运行：macOS 14 或更新版本；macOS 26 支持系统的透明 / 着色玻璃外观。
- 从源码构建：完整 Xcode 26 或更新版本。
- 使用已构建的应用无需安装 Python 或 Xcode。

### 构建与安装

在项目目录运行：

```bash
./macos/widgetkit/build-widget.command
```

脚本生成并打开 `macos/widgetkit/build/Build/Products/Release/Codex Reset.app`，使用本机临时签名，不要求 Apple 开发者账号。建议将完整应用复制到“应用程序”文件夹，再打开应用并添加小组件；不要单独移动内部的 `.appex`。构建产物只包含当前 Mac 的处理器架构，在其他 Mac 上使用时需匹配架构或重新构建。

### 添加到桌面

1. 先打开一次 Codex Reset 应用。
2. 在桌面空白处右键，选择“编辑小组件”。
3. 搜索 **Codex Reset**，选择中号并添加到桌面。
4. 在系统设置的“桌面与程序坞”中，将小组件外观设为与天气、电池相同的透明 / 着色样式。

### 使用与刷新

小组件请求约每 30 分钟更新，实际时间和频率由系统控制。离线时保留上次成功数据；首次加载失败显示“—”，不会把未知概率显示成 0%。点击小组件打开配套应用，可以请求刷新或查看完整预告。预告在中号中为单行，在大号中可显示多行。

这是真正的桌面小组件，所以没有图钉、任意窗口置顶或双击刷新。配套应用可以关闭，小组件仍由系统管理。旧浮窗可从菜单栏退出。

### 源码与验证

用 Xcode 打开 `macos/widgetkit/CodexReset.xcodeproj`，选择 CodexReset 即可构建。`Shared/Radar.swift` 负责解析、网络与离线缓存；`Widget/CodexResetWidget.swift` 负责时间线与小组件内容；`App/CodexResetApp.swift` 是配套应用。

```bash
./macos/widgetkit/build-widget.command --no-open
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer xcrun swiftc \
  macos/widgetkit/Shared/Radar.swift macos/widgetkit/Tests/RadarTests.swift \
  -o /tmp/codex-radar-tests
/tmp/codex-radar-tests
```

### 旧版独立浮窗

原 AppKit 浮窗仍保留于 `macos/CodexReset.swift`，通过 `./macos/build.command` 构建。它适合需要置顶、自由拖动和定时刷新的场景；外观不等同于系统 WidgetKit 小组件。
