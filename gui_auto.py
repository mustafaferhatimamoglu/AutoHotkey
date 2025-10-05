from __future__ import annotations

import sys
import time
import threading
from typing import List, Dict, Optional, Tuple

import numpy as np
import cv2  # opencv-python
import mss
from PIL import Image  # noqa: F401  # For potential conversions if needed
import pyautogui
import keyboard
import pyperclip

import tkinter as tk
from tkinter import ttk

try:
    import winsound  # Windows-only beep
except Exception:  # pragma: no cover - non-Windows
    winsound = None


# -------------------------------
# Monitor utilities
# -------------------------------

def get_monitors() -> List[Dict[str, int]]:
    """Return a list of monitor dicts from mss().monitors[1:].

    Each monitor dict contains keys: left, top, width, height.
    """
    with mss.mss() as sct:
        # sct.monitors[0] is the virtual bounding box; ignore it
        monitors = [
            {
                "left": m["left"],
                "top": m["top"],
                "width": m["width"],
                "height": m["height"],
            }
            for m in sct.monitors[1:]
        ]
    return monitors


def point_monitor_index(x: int, y: int, monitors: List[Dict[str, int]]) -> int:
    """Return 1-based monitor index containing point (x, y); 0 if none."""
    for idx, m in enumerate(monitors, start=1):
        if (
            x >= m["left"]
            and y >= m["top"]
            and x < m["left"] + m["width"]
            and y < m["top"] + m["height"]
        ):
            return idx
    return 0


# -------------------------------
# Image search and click
# -------------------------------

def _load_templates(images: List[str]) -> List[Tuple[str, np.ndarray, Tuple[int, int]]]:
    loaded: List[Tuple[str, np.ndarray, Tuple[int, int]]] = []
    for path in images:
        try:
            tpl = cv2.imread(path, cv2.IMREAD_COLOR)
            if tpl is None:
                print(f"[warn] Could not read image: {path}")
                continue
            h, w = tpl.shape[:2]
            loaded.append((path, tpl, (w, h)))
        except Exception as e:
            print(f"[warn] Error reading image '{path}': {e}")
    return loaded


def find_and_click(
    images: List[str],
    threshold: float,
    retry_ms: int,
    timeout_ms: int,
) -> bool:
    """Search loop across all monitors for templates; click on first above threshold.

    - Captures each monitor via MSS.
    - Uses cv2.matchTemplate with TM_CCOEFF_NORMED.
    - Picks the single best match across all monitors/templates per iteration.
    - If best >= threshold, moves mouse and clicks, then returns True.
    - Retries until timeout; returns False if not found.
    """
    print(
        f"[info] Searching for images {images} with threshold={threshold}, retry={retry_ms}ms, timeout={timeout_ms}ms"
    )

    templates = _load_templates(images)
    if not templates:
        print("[error] No valid images to search. Aborting search.")
        return False

    start = time.monotonic()
    with mss.mss() as sct:
        monitors = [m for m in sct.monitors[1:]]
        while (time.monotonic() - start) * 1000 < timeout_ms:
            best_val: float = -1.0
            best_loc: Optional[Tuple[int, int]] = None
            best_tpl_size: Optional[Tuple[int, int]] = None
            best_monitor: Optional[Dict[str, int]] = None
            best_image_name: Optional[str] = None

            for mon in monitors:
                try:
                    frame = np.array(sct.grab(mon))  # BGRA
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                except Exception as e:
                    print(f"[warn] Screen grab failed for monitor {mon}: {e}")
                    continue

                for img_name, tpl, (tw, th) in templates:
                    try:
                        res = cv2.matchTemplate(
                            frame_bgr, tpl, cv2.TM_CCOEFF_NORMED
                        )
                        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
                    except Exception as e:
                        print(f"[warn] matchTemplate failed for {img_name}: {e}")
                        continue

                    if max_val > best_val:
                        best_val = max_val
                        best_loc = max_loc
                        best_tpl_size = (tw, th)
                        best_monitor = mon
                        best_image_name = img_name

            if best_val >= threshold and best_loc and best_tpl_size and best_monitor:
                gx = int(best_monitor["left"] + best_loc[0] + best_tpl_size[0] / 2)
                gy = int(best_monitor["top"] + best_loc[1] + best_tpl_size[1] / 2)
                mon_idx = 0
                # Compute monitor index (1-based) among active list
                for idx, mon in enumerate(monitors, start=1):
                    if mon is best_monitor:
                        mon_idx = idx
                        break

                print(
                    f"[match] {best_image_name} @ monitor#{mon_idx} score={best_val:.3f} center=({gx},{gy})"
                )
                try:
                    pyautogui.moveTo(gx, gy)
                    pyautogui.click()
                    print(f"[click] Clicked at ({gx},{gy})")
                    # After clicking, simulate pressing 'y'
                    time.sleep(0.1)
                    try:
                        pyautogui.press('y')
                        print("[key] Sent 'y'")
                    except Exception as e:
                        print(f"[warn] Failed to send 'y': {e}")
                except Exception as e:
                    print(f"[warn] pyautogui click failed: {e}")
                return True

            time.sleep(max(0.0, retry_ms / 1000.0))

    print("[debug] No image matched within timeout.")
    return False


# -------------------------------
# HUD and Toast via Tkinter
# -------------------------------

class Hud:
    def __init__(self, root: tk.Tk, monitors: List[Dict[str, int]]) -> None:
        self.root = root
        self.monitors = monitors
        self.win: Optional[tk.Toplevel] = None
        self.label: Optional[tk.Label] = None
        self.job: Optional[str] = None

    def show(self) -> None:
        if self.win is not None:
            return
        self.win = tk.Toplevel(self.root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        try:
            self.win.attributes("-alpha", 0.9)
        except Exception:
            pass

        frame = ttk.Frame(self.win, padding=(8, 6))
        frame.pack(fill=tk.BOTH, expand=True)
        self.label = tk.Label(
            frame,
            text="",
            font=("Segoe UI", 10, "bold"),
            bg="#222222",
            fg="#f0f0f0",
            padx=8,
            pady=4,
        )
        self.label.pack()
        self._update()

    def hide(self) -> None:
        if self.job is not None:
            try:
                self.root.after_cancel(self.job)
            except Exception:
                pass
            self.job = None
        if self.win is not None:
            try:
                self.win.destroy()
            except Exception:
                pass
            self.win = None
            self.label = None

    def _update(self) -> None:
        try:
            pos = pyautogui.position()
            x, y = int(pos.x), int(pos.y)
        except Exception:
            x, y = 0, 0
        mon_idx = point_monitor_index(x, y, self.monitors)
        if self.label and self.win:
            self.label.config(text=f"X: {x}  Y: {y}  Mon: {mon_idx}")
            # Position near current monitor's top-right
            mon: Optional[Dict[str, int]] = (
                self.monitors[mon_idx - 1] if 1 <= mon_idx <= len(self.monitors) else None
            )
            if mon:
                self.win.update_idletasks()
                ww = self.win.winfo_width()
                wh = self.win.winfo_height()
                nx = mon["left"] + mon["width"] - ww - 20
                ny = mon["top"] + 20
                try:
                    self.win.geometry(f"{ww}x{wh}+{nx}+{ny}")
                except Exception:
                    pass
        self.job = self.root.after(30, self._update)


def show_toast(
    root: tk.Tk,
    monitors: List[Dict[str, int]],
    text: str,
    duration_ms: int = 800,
    bg: str = "#333333",
    fg: str = "#ffffff",
    wraplength: int = 460,
) -> None:
    win = tk.Toplevel(root)
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    try:
        win.attributes("-alpha", 0.92)
    except Exception:
        pass
    frame = ttk.Frame(win, padding=(8, 6))
    frame.pack(fill=tk.BOTH, expand=True)
    label = tk.Label(
        frame,
        text=text,
        font=("Segoe UI", 10, "bold"),
        bg=bg,
        fg=fg,
        padx=10,
        pady=6,
        wraplength=wraplength,
        justify="left",
    )
    label.pack()

    # Position near top-right of current monitor
    try:
        pos = pyautogui.position()
        x, y = int(pos.x), int(pos.y)
    except Exception:
        x, y = 0, 0
    idx = point_monitor_index(x, y, monitors)
    mon = monitors[idx - 1] if 1 <= idx <= len(monitors) else monitors[0]
    win.update_idletasks()
    ww = win.winfo_width()
    wh = win.winfo_height()
    nx = mon["left"] + mon["width"] - ww - 20
    ny = mon["top"] + 20
    try:
        win.geometry(f"{ww}x{wh}+{nx}+{ny}")
    except Exception:
        pass

    def _destroy():
        try:
            win.destroy()
        except Exception:
            pass

    root.after(duration_ms, _destroy)


def _alert_not_found(root: tk.Tk, monitors: List[Dict[str, int]]) -> None:
    show_toast(root, monitors, "Image not found", duration_ms=1500, bg="#bb2222", fg="#ffffff")
    if winsound:
        try:
            winsound.Beep(800, 250)
        except Exception:
            try:
                winsound.MessageBeep()
            except Exception:
                pass
    else:
        # Fallback ASCII bell
        sys.stdout.write("\a")
        sys.stdout.flush()


# -------------------------------
# Hotkey handlers and main
# -------------------------------

def _show_start_instructions(root: tk.Tk, monitors: List[Dict[str, int]]) -> None:
    msg = (
        "Kısayollar: F8 = HUD, Ctrl+Shift+C = Koordinat kopyala, ESC = Çıkış\n"
        "Sürekli arama aktif. Eşleşme sonrası 'y' gönderilir ve 3 sn beklenir."
    )
    show_toast(root, monitors, msg, duration_ms=8000)

def main() -> None:
    # Config: adjust as needed or pass image names via argv
    # Example usage: python gui_auto.py accept_green.png accept_green-2.png
    images_to_search: List[str] = sys.argv[1:] or ["accept_green.png", "accept_green-2.png", "accept_green-3.png", "accept_green-4.png","accept_green-5.png","accept_green-6.png","accept_green-7.png","Codex_wants_to_run.png"]
    threshold: float = 0.85
    retry_ms: int = 120
    timeout_ms: int = 6000

    # Get monitors
    monitors = get_monitors()
    if not monitors:
        print("[error] No monitors detected via MSS.")
        return

    # Tkinter root (runs in main thread)
    root = tk.Tk()
    root.withdraw()  # Keep hidden; HUD/Toast are Toplevels

    hud = Hud(root, monitors)

    # Background worker: continuous search with cooldown after 'y'
    stop_event = threading.Event()

    def _runner() -> None:
        first_run = True
        while not stop_event.is_set():
            found_local = find_and_click(images_to_search, threshold, retry_ms, timeout_ms)
            if found_local:
                # Cooldown to prevent rapid repeats
                print("[cooldown] Sleeping 3.0s after sending 'y'")
                t_end = time.monotonic() + 3.0
                while time.monotonic() < t_end and not stop_event.is_set():
                    time.sleep(0.05)
            else:
                if first_run:
                    root.after(0, lambda: _alert_not_found(root, monitors))
                # Small breather between cycles
                time.sleep(0.05)
            first_run = False

    worker = threading.Thread(target=_runner, name="finder", daemon=True)
    worker.start()

    # Hotkeys
    keyboard.on_press_key("f8", lambda e: root.after(0, hud.show))
    keyboard.on_release_key("f8", lambda e: root.after(0, hud.hide))

    def _copy_coords() -> None:
        try:
            pos = pyautogui.position()
            x, y = int(pos.x), int(pos.y)
            pyperclip.copy(f"{x},{y}")
            show_toast(root, monitors, f"Copied: {x},{y}")
        except Exception as e:
            show_toast(root, monitors, f"Copy failed: {e}", bg="#bb2222")

    keyboard.add_hotkey("ctrl+shift+c", lambda: root.after(0, _copy_coords))

    # Safe shutdown on ESC
    def _on_exit() -> None:
        try:
            hud.hide()
        finally:
            try:
                stop_event.set()
            except Exception:
                pass
            try:
                root.quit()
            except Exception:
                pass
            try:
                root.destroy()
            except Exception:
                pass
            # Allow keyboard hooks to unwind
            try:
                keyboard.unhook_all()
            except Exception:
                pass

    keyboard.add_hotkey("esc", _on_exit)

    # Show startup instructions and print usage
    _show_start_instructions(root, monitors)
    print("Ready. Continuous search running.")
    print("Press F8 to show mouse coords; Ctrl+Shift+C to copy coords; ESC to quit.")

    # Enter Tk event loop (non-blocking for hotkey handlers)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        _on_exit()


if __name__ == "__main__":
    main()
