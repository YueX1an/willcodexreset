# Codex Reset 桌面小组件

Windows 桌面悬浮卡片，显示 [willcodexreset.com](https://willcodexreset.com/) 的未来 24 / 48 小时重置概率、状态、上次确认重置时间和预告。卡片会模糊当前位置的桌面背景，并保留背景的颜色与轮廓。

## 安装与启动

需要 Windows、Python 3.10 或更新版本，以及可用的 Tkinter。安装两个运行依赖：

```powershell
python -m pip install Pillow pystray
```

在本目录运行：

```powershell
pythonw codex_reset_widget.py
```

`pythonw` 不显示控制台；排查启动或网络问题时，改用 `python codex_reset_widget.py` 查看错误输出。请使用安装了上述依赖的同一个 Python 环境。每次修改脚本后，先从托盘菜单退出旧实例，再重新启动。

## 使用

| 操作 | 效果 |
| --- | --- |
| 拖动卡片 | 移动位置，并重新采样该位置的桌面背景 |
| 点击右上角图钉 | 切换置顶；图钉变蓝表示已置顶 |
| 双击卡片 | 立即刷新数据 |
| 右键卡片 | 打开“隐藏到托盘、置顶/取消置顶、立即刷新、退出”菜单 |
| 点击通知区域的 Codex Reset 图标 | 显示或隐藏卡片 |

卡片默认每 10 分钟从 `https://willcodexreset.com/api/reset-radar` 刷新一次。抓取失败时会显示离线状态并等待下一次刷新。窗口不占任务栏位置；托盘图标位于 Windows 通知区域，是否收进 `^` 隐藏图标由 Windows 的任务栏设置决定。

磨砂背景在启动、拖动结束和从托盘重新显示时更新；桌面壁纸或其他窗口变化后，可以轻拖卡片让背景重新采样。

## 外观设置

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

## 测试

```powershell
python -m pip install pytest
python -m pytest tests -q
```

数据处理在 `codex_reset_data.py`，界面和托盘逻辑在 `codex_reset_widget.py`。
