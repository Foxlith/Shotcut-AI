import time
import subprocess
import ctypes
import win32gui
import win32ui
from PIL import Image

SHOTCUT_EXE = r"C:\Users\Fox\AppData\Local\Programs\Shotcut\shotcut.exe"
THEME_QSS = r"C:\Users\Fox\Desktop\Shotcut-AI\capcut_theme.qss"
DEMO_PROJECT = r"C:\Users\Fox\Desktop\Proyecto_Prueba_Shotcut_AI.mlt"
OUTPUT_PNG = r"C:\Users\Fox\.gemini\antigravity\brain\1442048b-4336-4334-9cd3-3bd08001dafc\shotcut_ui_current.png"

def capture_window(hwnd, save_path):
    rect = win32gui.GetWindowRect(hwnd)
    w = rect[2] - rect[0]
    h = rect[3] - rect[1]
    
    hwnd_dc = win32gui.GetWindowDC(hwnd)
    mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
    save_dc = mfc_dc.CreateCompatibleDC()
    
    save_bitmap = win32ui.CreateBitmap()
    save_bitmap.CreateCompatibleBitmap(mfc_dc, w, h)
    save_dc.SelectObject(save_bitmap)
    
    ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 2)
    bmpinfo = save_bitmap.GetInfo()
    bmpstr = save_bitmap.GetBitmapBits(True)
    
    im = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRX', 0, 1)
    im.save(save_path)
    
    win32gui.DeleteObject(save_bitmap.GetHandle())
    save_dc.DeleteDC()
    mfc_dc.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwnd_dc)
    print("Capture succeeded, saved to:", save_path)

def find_w():
    found = []
    def enum_cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            rect = win32gui.GetWindowRect(hwnd)
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]
            if "shotcut" in title.lower() and w > 600 and h > 400:
                found.append(hwnd)
    win32gui.EnumWindows(enum_cb, None)
    return found

print("Launching Shotcut...")
p = subprocess.Popen([SHOTCUT_EXE, "-stylesheet", THEME_QSS, DEMO_PROJECT])
for _ in range(25):
    time.sleep(0.4)
    hwnds = find_w()
    if hwnds:
        break

if hwnds:
    time.sleep(2.0)
    capture_window(hwnds[0], OUTPUT_PNG)
    # Terminate after capture
    p.terminate()
