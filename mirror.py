# mirror.py
# Top 5 complexidade:
# 1) PipWindow._blit_source     O(1) GDI StretchBlt
# 2) TrayApp._build_menu        O(n) — monta menu da bandeja
# 3) list_monitors              O(n) — enumera monitores
# 4) PipWindow._tick            O(1)
# 5) scale_to_fit               O(1)

"""Monitor Mirror — PiP na bandeja (fonte escolhida → sempre no primário)."""

from __future__ import annotations

import ctypes
import queue
from ctypes import wintypes
from dataclasses import dataclass
from typing import Callable, Optional

import pystray
import tkinter as tk
from PIL import Image, ImageDraw

# GDI StretchBlt é barato; 15 FPS basta para PiP.
TARGET_FPS = 15
TICK_MS = max(1, int(1000 / TARGET_FPS))
PIP_WIDTH_RATIO = 0.28
PIP_MARGIN = 24
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000
SRCCOPY = 0x00CC0020
HALFTONE = 4

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32


@dataclass(frozen=True)
class MonitorInfo:
    index: int
    left: int
    top: int
    width: int
    height: int
    is_primary: bool
    name: str

    @property
    def short_label(self) -> str:
        role = "primário" if self.is_primary else "secundário"
        return f"{self.name} — {self.width}x{self.height} ({role})"


class _MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32),
    ]


class _DISPLAY_DEVICEW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("DeviceName", wintypes.WCHAR * 32),
        ("DeviceString", wintypes.WCHAR * 128),
        ("StateFlags", wintypes.DWORD),
        ("DeviceID", wintypes.WCHAR * 128),
        ("DeviceKey", wintypes.WCHAR * 128),
    ]


def scale_to_fit(
    src_w: int, src_h: int, dst_w: int, dst_h: int
) -> tuple[int, int]:
    """Calcula tamanho letterbox preservando aspect ratio. O(1)."""
    if src_w <= 0 or src_h <= 0 or dst_w <= 0 or dst_h <= 0:
        return (1, 1)
    scale = min(dst_w / src_w, dst_h / src_h)
    return (max(1, int(src_w * scale)), max(1, int(src_h * scale)))


def _adapter_name(device_name: str) -> str:
    """Resolve nome do adaptador. O(n)."""
    index = 0
    while True:
        adapter = _DISPLAY_DEVICEW()
        adapter.cb = ctypes.sizeof(adapter)
        if not user32.EnumDisplayDevicesW(None, index, ctypes.byref(adapter), 0):
            break
        if adapter.DeviceName == device_name:
            return str(adapter.DeviceString).strip() or device_name
        index += 1
    return device_name


def _monitor_chip_hint(device_name: str) -> str:
    """Extrai hint do hardware (GSM=LG, MTT=VDD). O(1)."""
    monitor = _DISPLAY_DEVICEW()
    monitor.cb = ctypes.sizeof(monitor)
    if not user32.EnumDisplayDevicesW(device_name, 0, ctypes.byref(monitor), 0):
        return ""
    parts = str(monitor.DeviceID).split("\\")
    if len(parts) >= 2 and parts[0].upper() == "MONITOR":
        return parts[1]
    return ""


def list_monitors() -> list[MonitorInfo]:
    """Lista monitores via Win32, índice alinhado ao dxcam. O(n)."""
    collected: list[dict] = []

    def _callback(hmonitor, _hdc, _lprect, _lparam):  # type: ignore[no-untyped-def]
        info = _MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(info)
        if not user32.GetMonitorInfoW(hmonitor, ctypes.byref(info)):
            return 1
        rect = info.rcMonitor
        adapter = _adapter_name(info.szDevice)
        chip = _monitor_chip_hint(info.szDevice)
        name = f"{adapter} ({chip})" if chip and chip not in adapter else adapter
        collected.append(
            {
                "left": int(rect.left),
                "top": int(rect.top),
                "width": int(rect.right - rect.left),
                "height": int(rect.bottom - rect.top),
                "is_primary": bool(info.dwFlags & 1),
                "name": name,
            }
        )
        return 1

    monitor_enum_proc = ctypes.WINFUNCTYPE(
        ctypes.c_int,
        wintypes.HMONITOR,
        wintypes.HDC,
        ctypes.POINTER(wintypes.RECT),
        wintypes.LPARAM,
    )
    user32.EnumDisplayMonitors(0, 0, monitor_enum_proc(_callback), 0)
    collected.sort(key=lambda item: (not item["is_primary"], item["left"], item["top"]))

    return [
        MonitorInfo(
            index=index,
            left=item["left"],
            top=item["top"],
            width=item["width"],
            height=item["height"],
            is_primary=item["is_primary"],
            name=item["name"],
        )
        for index, item in enumerate(collected)
    ]


def make_tray_icon(size: int = 64) -> Image.Image:
    """Ícone simples de PiP para a bandeja. O(1)."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = size // 10
    draw.rounded_rectangle(
        (margin, margin, size - margin, size - margin),
        radius=size // 6,
        fill=(30, 30, 30, 255),
        outline=(80, 180, 255, 255),
        width=max(2, size // 16),
    )
    inset = size // 3
    draw.rounded_rectangle(
        (inset, inset, size - margin - 2, size - margin - 2),
        radius=size // 10,
        fill=(80, 180, 255, 255),
    )
    return img


def pip_geometry(primary: MonitorInfo, source: MonitorInfo) -> tuple[int, int, int, int]:
    """Tamanho/posição do PiP no canto inferior direito do primário. O(1)."""
    pip_w = max(320, int(primary.width * PIP_WIDTH_RATIO))
    aspect = source.width / max(1, source.height)
    pip_h = max(180, int(pip_w / aspect))
    max_h = int(primary.height * 0.45)
    if pip_h > max_h:
        pip_h = max_h
        pip_w = max(320, int(pip_h * aspect))
    left = primary.left + primary.width - pip_w - PIP_MARGIN
    top = primary.top + primary.height - pip_h - PIP_MARGIN
    return pip_w, pip_h, left, top


class PipWindow:
    """Janela PiP borderless sempre no monitor primário."""

    def __init__(self, root: tk.Tk, primary: MonitorInfo) -> None:
        self.root = root
        self.primary = primary
        self.source: Optional[MonitorInfo] = None
        self._running = True
        self._visible = False
        self._tick_scheduled = False
        self._drag_ox = 0
        self._drag_oy = 0

        self.win = tk.Toplevel(root)
        self.win.withdraw()
        self.win.overrideredirect(True)
        self.win.configure(bg="black", cursor="fleur")
        self.win.attributes("-topmost", True)
        self.win.bind("<Escape>", lambda _e: self.hide())
        self.win.bind("<ButtonPress-1>", self._start_drag)
        self.win.bind("<B1-Motion>", self._on_drag)
        # Sem Canvas/ImageTk: StretchBlt GDI direto no HWND (CPU baixa).

    def _apply_tool_window(self) -> None:
        """Remove da barra de tarefas (WS_EX_TOOLWINDOW). O(1)."""
        self.win.update_idletasks()
        hwnd = self.win.winfo_id()
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style = (style | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)

    def _start_drag(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        self._drag_ox = event.x_root - self.win.winfo_x()
        self._drag_oy = event.y_root - self.win.winfo_y()

    def _on_drag(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        self.win.geometry(f"+{event.x_root - self._drag_ox}+{event.y_root - self._drag_oy}")

    def set_source(self, source: MonitorInfo) -> None:
        """Troca o monitor capturado e mostra o PiP. O(1)."""
        if source.is_primary:
            return
        self.source = source
        pip_w, pip_h, left, top = pip_geometry(self.primary, source)
        self.win.geometry(f"{pip_w}x{pip_h}+{left}+{top}")
        self.show()

    def show(self) -> None:
        """Exibe PiP e retoma blit GDI (sai do idle). O(1)."""
        if self.source is None:
            return
        self._visible = True
        self.win.deiconify()
        self._apply_tool_window()
        self.win.attributes("-topmost", True)
        self.win.lift()
        self._schedule_tick()

    def hide(self) -> None:
        """Oculta PiP e para o loop (idle ~0% CPU). O(1)."""
        self._visible = False
        self.win.withdraw()

    def toggle_visible(self) -> None:
        if self._visible:
            self.hide()
        elif self.source is not None:
            self.show()

    def shutdown(self) -> None:
        self._running = False
        self._visible = False
        try:
            self.win.destroy()
        except tk.TclError:
            pass

    def _schedule_tick(self) -> None:
        """Agenda próximo frame só se visível. O(1)."""
        if not self._running or not self._visible or self._tick_scheduled:
            return
        self._tick_scheduled = True
        self.root.after(TICK_MS, self._tick)

    def _blit_source(self) -> None:
        """Copia o monitor fonte → janela PiP via StretchBlt. O(1) GDI."""
        if self.source is None:
            return
        self.win.update_idletasks()
        hwnd = int(self.win.winfo_id())
        dst_w = max(1, self.win.winfo_width())
        dst_h = max(1, self.win.winfo_height())
        hdc_screen = user32.GetDC(0)
        hdc_dst = user32.GetDC(hwnd)
        if not hdc_screen or not hdc_dst:
            if hdc_screen:
                user32.ReleaseDC(0, hdc_screen)
            if hdc_dst:
                user32.ReleaseDC(hwnd, hdc_dst)
            return
        try:
            gdi32.SetStretchBltMode(hdc_dst, HALFTONE)
            gdi32.StretchBlt(
                hdc_dst,
                0,
                0,
                dst_w,
                dst_h,
                hdc_screen,
                self.source.left,
                self.source.top,
                self.source.width,
                self.source.height,
                SRCCOPY,
            )
        finally:
            user32.ReleaseDC(hwnd, hdc_dst)
            user32.ReleaseDC(0, hdc_screen)

    def _tick(self) -> None:
        """Blita 1 frame GDI. Idle = não reagenda."""
        self._tick_scheduled = False
        if not self._running or not self._visible:
            return
        self._blit_source()
        self._schedule_tick()


class TrayApp:
    """App de bandeja: botão direito escolhe o monitor fonte do PiP."""

    def __init__(self) -> None:
        self.monitors = list_monitors()
        self.primary = next((m for m in self.monitors if m.is_primary), None)
        if self.primary is None:
            raise RuntimeError("Monitor primário não encontrado.")

        self.sources = [m for m in self.monitors if not m.is_primary]
        if not self.sources:
            raise RuntimeError("Nenhum monitor secundário para PiP.")

        self.selected_index = self.sources[0].index
        self.commands: queue.Queue[tuple[str, Optional[int]]] = queue.Queue()

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("Monitor Mirror")
        self.pip = PipWindow(self.root, self.primary)

        self.icon = pystray.Icon(
            "monitor-mirror",
            make_tray_icon(),
            "Monitor Mirror PiP",
            menu=self._build_menu(),
        )

        self.root.after(100, self._poll_commands)
        self.root.after(200, self._auto_start_default)

    def _build_menu(self) -> pystray.Menu:
        """Monta menu de contexto da bandeja. O(n)."""
        items: list[pystray.MenuItem] = [
            pystray.MenuItem(
                "Monitor fonte (PiP)",
                lambda: None,
                enabled=False,
            ),
        ]
        for mon in self.sources:
            items.append(
                pystray.MenuItem(
                    mon.short_label,
                    self._make_select_handler(mon.index),
                    checked=self._make_checked(mon.index),
                    radio=True,
                )
            )
        items.extend(
            [
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "Mostrar / ocultar PiP",
                    self._on_toggle,
                    default=True,
                ),
                pystray.MenuItem("Sair", self._on_quit),
            ]
        )
        return pystray.Menu(*items)

    def _make_select_handler(self, index: int) -> Callable[..., None]:
        def _handler(_icon: pystray.Icon, _item: pystray.MenuItem) -> None:
            self.commands.put(("select", index))

        return _handler

    def _make_checked(self, index: int) -> Callable[[pystray.MenuItem], bool]:
        def _checked(_item: pystray.MenuItem) -> bool:
            return self.selected_index == index

        return _checked

    def _on_toggle(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        self.commands.put(("toggle", None))

    def _on_quit(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        self.commands.put(("quit", None))

    def _auto_start_default(self) -> None:
        self._select_source(self.selected_index)

    def _select_source(self, index: int) -> None:
        source = next((m for m in self.sources if m.index == index), None)
        if source is None:
            return
        self.selected_index = index
        self.pip.set_source(source)
        self.icon.title = f"PiP ← {source.short_label}"
        try:
            self.icon.menu = self._build_menu()
            self.icon.update_menu()
        except Exception:
            pass

    def _poll_commands(self) -> None:
        """Consome fila da bandeja no thread do Tk. O(k)."""
        try:
            while True:
                action, value = self.commands.get_nowait()
                if action == "select" and value is not None:
                    self._select_source(value)
                elif action == "toggle":
                    self.pip.toggle_visible()
                elif action == "quit":
                    self._shutdown()
                    return
        except queue.Empty:
            pass
        self.root.after(100, self._poll_commands)

    def _shutdown(self) -> None:
        self.pip.shutdown()
        try:
            self.icon.stop()
        except Exception:
            pass
        self.root.after(0, self.root.destroy)

    def run(self) -> None:
        self.icon.run_detached()
        self.root.mainloop()


def main() -> None:
    # Nome amigável no Task Manager / jumplists (Windows).
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "canetex.MonitorMirrorPiP"
        )
    except Exception:
        pass
    TrayApp().run()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        from pathlib import Path

        log_path = Path(__file__).with_name("crash.log")
        log_path.write_text(traceback.format_exc(), encoding="utf-8")
        raise
