import ctypes
from codex_reset_widget import Widget


def test_visible_tk_wrapper_uses_tool_window_style(monkeypatch):
    monkeypatch.setattr(Widget, "refresh", lambda self: None)
    monkeypatch.setattr(Widget, "_start_tray", lambda self: None)
    monkeypatch.setattr(Widget, "_update_background", lambda self: None)
    widget = Widget()
    try:
        widget.root.update_idletasks()
        wrapper = ctypes.windll.user32.GetAncestor(widget.root.winfo_id(), 2)
        assert wrapper and wrapper != widget.root.winfo_id()

        exstyle = ctypes.windll.user32.GetWindowLongW(wrapper, -20)
        assert exstyle & 0x00000080  # WS_EX_TOOLWINDOW hides the taskbar entry
        assert not exstyle & 0x00040000  # WS_EX_APPWINDOW forces one

        widget.root.withdraw()
        widget.root.update_idletasks()
        widget.root.deiconify()
        widget.root.update_idletasks()
        exstyle = ctypes.windll.user32.GetWindowLongW(wrapper, -20)
        assert exstyle & 0x00000080
    finally:
        widget.root.destroy()
