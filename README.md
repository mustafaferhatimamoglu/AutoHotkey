# GUI Automation via Image Matching (Windows, Python 3.11)

This repository contains a single Python 3.11 script that automates GUI tasks on Windows using multi‑monitor screenshots and OpenCV template matching. It also provides global hotkeys and a lightweight on‑screen HUD.

- Image search: OpenCV `TM_CCOEFF_NORMED` across all physical monitors via MSS
- Clicks: Moves mouse and clicks the highest‑score match above threshold
- HUD: F8 (hold) shows mouse X,Y and monitor index in a small, top‑right overlay
- Clipboard: Ctrl+Shift+C copies current "x,y" to clipboard with a quick toast
- Safe exit: ESC quits cleanly

## Files
- `gui_auto.py` — Main script
- `requirements.txt` — Python dependencies

## Requirements
- Windows 10/11
- Python 3.11 (includes Tkinter on standard installers)
- Ability to install Python packages (may require admin for global install)

## Install
```bat
:: Optional: create and activate a virtual environment
py -3.11 -m venv .venv
.\.venv\Scripts\activate

:: Install dependencies
pip install -r requirements.txt
```

## Usage
1. Prepare the template images you want to search for (e.g. `accept_green.png`, `accept_green-2.png`). Place them in the working directory.
2. Run the script passing one or more image filenames:
```bat
python gui_auto.py accept_green.png accept_green-2.png
```
3. The script searches all physical monitors for the best match above the threshold and clicks it. If none is found within the timeout, it beeps and shows a red toast “Image not found”.

### Hotkeys
- F8 (press & hold): Show HUD with `X`, `Y`, and monitor index
- Ctrl+Shift+C: Copy current mouse coordinates as `x,y` to clipboard (toast shown)
- ESC: Quit the program

### Configuration
Edit the values at the top of `main()` in `gui_auto.py` if needed:
- `threshold = 0.85` — match confidence threshold (0..1)
- `retry_ms = 120` — delay between retries
- `timeout_ms = 6000` — overall timeout for the initial search

You can also omit CLI args; defaults are `accept_green.png` and `accept_green-2.png`.

## How It Works
- Monitors: Uses `mss().monitors[1:]` to iterate only physical monitors. `monitors[0]` is the virtual bounding box and is ignored.
- Capture: Grabs `BGRA` frames for each monitor, converts to `BGR` for OpenCV.
- Matching: `cv2.matchTemplate(..., TM_CCOEFF_NORMED)` for each template and monitor; selects the highest score. If `score >= threshold`, it computes the center in global coordinates and clicks via `pyautogui`.
- HUD/Toast: A borderless, topmost Tkinter window updates every 30ms. It’s positioned near the top‑right of the active monitor.

## Tips & Troubleshooting
- Run as Administrator if hotkeys do not register or if you need to interact with elevated apps (UAC). The `keyboard` library and `pyautogui` may require admin to control or listen globally in some configurations.
- Template quality matters: capture your template at the same scale as on screen (DPI/scaling can vary by monitor). Try adjusting the `threshold` (e.g., 0.8–0.93).
- If images never match:
  - Verify paths and filenames (OpenCV returns `None` if the file isn’t found or is invalid).
  - Reduce `threshold` slightly.
  - Ensure the element is fully visible and not obstructed.
- Multi‑monitor: The script automatically searches all monitors and computes global coordinates correctly; no scaling assumptions.
- Dependencies: `pyautogui` confidence‑based searching needs OpenCV installed, but this script uses OpenCV directly for matching.

## Uninstall / Clean Up
If you used a virtual environment, just deactivate and delete the folder:
```bat
deactivate
rd /s /q .venv
```

## License
Not specified by the task. Use internally or add your own license if needed.

