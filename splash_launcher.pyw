"""
Shotcut AI — Modern Animated Splash Launcher
Features:
- Displays new dark minimalist logo (Carbón & Titanio)
- High-tech top-to-bottom cyan laser scanline animation
- Aggressively suppresses/hides legacy internal splash screen from shotcut.exe
- Launches Shotcut with modern QSS theme
- Hands off focus cleanly once main editing window is loaded
"""

import os
import sys
import time
import subprocess
import threading
import tkinter as tk
from PIL import Image, ImageTk

try:
    import win32gui
    import win32process
    import win32api
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

SHOTCUT_EXE = r"C:\Users\Fox\AppData\Local\Programs\Shotcut\shotcut.exe"
THEME_QSS = r"C:\Users\Fox\Desktop\Shotcut-AI\capcut_theme.qss"
DEMO_PROJECT = r"C:\Users\Fox\Desktop\Proyecto_Prueba_Shotcut_AI.mlt"
LOGO_PATH = r"C:\Users\Fox\Desktop\Shotcut-AI\icons\shotcut-logo-320x320.png"

class ShotcutAiSplash:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        
        # Dimensions & positioning
        self.width = 500
        self.height = 440
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - self.width) // 2
        y = (screen_h - self.height) // 2
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")
        self.root.configure(bg="#16161a")

        # Canvas for drawing elements and animation
        self.canvas = tk.Canvas(
            self.root,
            width=self.width,
            height=self.height,
            bg="#16161a",
            highlightthickness=1,
            highlightbackground="#363644"
        )
        self.canvas.pack(fill="both", expand=True)

        # Subtle card header accent line
        self.canvas.create_line(0, 0, self.width, 0, fill="#20e6c5", width=3)

        # Load & prepare logo
        self.logo_size = 210
        raw_logo = Image.open(LOGO_PATH).convert("RGBA")
        raw_logo = raw_logo.resize((self.logo_size, self.logo_size), Image.Resampling.LANCZOS)
        self.logo_tk = ImageTk.PhotoImage(raw_logo)
        
        # Center logo
        self.logo_x = self.width // 2
        self.logo_y = 150
        self.canvas.create_image(self.logo_x, self.logo_y, image=self.logo_tk)

        # Branding text
        self.canvas.create_text(
            self.width // 2, 290,
            text="S H O T C U T   A I",
            font=("Segoe UI", 17, "bold"),
            fill="#f0f0f5"
        )
        
        self.status_text_id = self.canvas.create_text(
            self.width // 2, 325,
            text="Iniciando entorno creativo...",
            font=("Segoe UI", 10),
            fill="#9b9ba8"
        )

        # Progress track
        self.bar_w = 240
        self.bar_x1 = (self.width - self.bar_w) // 2
        self.bar_x2 = self.bar_x1 + self.bar_w
        self.bar_y = 360
        self.canvas.create_rectangle(
            self.bar_x1, self.bar_y, self.bar_x2, self.bar_y + 3,
            fill="#2c2c36", outline=""
        )
        self.progress_bar_id = self.canvas.create_rectangle(
            self.bar_x1, self.bar_y, self.bar_x1 + 10, self.bar_y + 3,
            fill="#20e6c5", outline=""
        )

        # Top-to-Bottom laser scanline animation setup
        # The beam travels from y = 35 down to y = 265 (covering the entire logo area)
        self.scan_min_y = 35
        self.scan_max_y = 265
        self.scan_y = self.scan_min_y
        self.scan_speed = 3.5
        self.running = True

        # Glow trails behind scanline
        self.trail_id2 = self.canvas.create_line(
            self.logo_x - 90, self.scan_y - 3,
            self.logo_x + 90, self.scan_y - 3,
            fill="#0d594c", width=6
        )
        self.trail_id1 = self.canvas.create_line(
            self.logo_x - 110, self.scan_y - 1,
            self.logo_x + 110, self.scan_y - 1,
            fill="#18b098", width=3
        )
        self.scan_line_id = self.canvas.create_line(
            self.logo_x - 125, self.scan_y,
            self.logo_x + 125, self.scan_y,
            fill="#20e6c5", width=2
        )

        # Start animation loop
        self.progress = 0
        self.animate_scanline()

        # Start process killer / splash suppressor thread
        self.suppress_legacy_splash = True
        threading.Thread(target=self.suppress_old_splash_loop, daemon=True).start()

        # Start Shotcut launch & monitor thread
        threading.Thread(target=self.launch_and_monitor, daemon=True).start()

    def animate_scanline(self):
        if not self.running:
            return
        
        self.scan_y += self.scan_speed
        if self.scan_y > self.scan_max_y:
            self.scan_y = self.scan_min_y

        self.canvas.coords(
            self.scan_line_id,
            self.logo_x - 125, self.scan_y,
            self.logo_x + 125, self.scan_y
        )
        self.canvas.coords(
            self.trail_id1,
            self.logo_x - 110, self.scan_y - 1,
            self.logo_x + 110, self.scan_y - 1
        )
        self.canvas.coords(
            self.trail_id2,
            self.logo_x - 90, self.scan_y - 3,
            self.logo_x + 90, self.scan_y - 3
        )

        # Smooth progress bar crawl
        if self.progress < 0.95:
            self.progress += 0.005
            cur_w = self.bar_x1 + int(self.bar_w * self.progress)
            self.canvas.coords(self.progress_bar_id, self.bar_x1, self.bar_y, cur_w, self.bar_y + 3)

        self.root.after(16, self.animate_scanline)

    def suppress_old_splash_loop(self):
        """Ultra-fast, zero-overhead interceptor that instantly banishes the old splash off-screen."""
        if not HAS_WIN32:
            return
        
        while self.running and self.suppress_legacy_splash:
            try:
                def enum_suppress(hwnd, _):
                    try:
                        title = win32gui.GetWindowText(hwnd)
                        if title == "Shotcut":
                            rect = win32gui.GetWindowRect(hwnd)
                            w = rect[2] - rect[0]
                            h = rect[3] - rect[1]
                            # Exactly matches the 320x320 legacy splash window
                            if 100 < w < 650 and 100 < h < 650:
                                win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
                                win32gui.SetWindowPos(
                                    hwnd, 0, -20000, -20000, 0, 0,
                                    win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_HIDEWINDOW
                                )
                    except Exception:
                        pass

                win32gui.EnumWindows(enum_suppress, None)
            except Exception:
                pass
            time.sleep(0.01)  # Lightning fast 10ms poll ensures it is banished instantly

    def launch_and_monitor(self):
        time.sleep(0.2)
        self.canvas.itemconfig(self.status_text_id, text="Cargando complementos y tema moderno...")

        cmd = [
            SHOTCUT_EXE,
            "--nosplash",
            "-stylesheet", THEME_QSS,
            DEMO_PROJECT
        ]
        
        env = os.environ.copy()
        env["SHOTCUT_NO_SPLASH"] = "1"
        env["SHOTCUT_WATCHDOG"] = "1"

        try:
            subprocess.Popen(
                cmd,
                env=env,
                cwd=os.path.dirname(SHOTCUT_EXE)
            )
        except Exception as e:
            self.canvas.itemconfig(self.status_text_id, text=f"Error al abrir: {e}")
            time.sleep(3)
            self.close_splash()
            return

        # Monitor for the actual main editing window
        start_time = time.time()
        while time.time() - start_time < 25:
            time.sleep(0.25)
            if HAS_WIN32:
                found_main = False
                def enum_main(hwnd, ctx):
                    if win32gui.IsWindowVisible(hwnd):
                        rect = win32gui.GetWindowRect(hwnd)
                        w = rect[2] - rect[0]
                        h = rect[3] - rect[1]
                        title = win32gui.GetWindowText(hwnd)
                        class_name = win32gui.GetClassName(hwnd)
                        # Main window is large and has Shotcut in title
                        if w > 700 and h > 500 and "Shotcut" in title:
                            ctx["found"] = True
                            ctx["hwnd"] = hwnd
                
                ctx = {"found": False, "hwnd": None}
                try:
                    win32gui.EnumWindows(enum_main, ctx)
                    if ctx["found"]:
                        self.canvas.itemconfig(self.status_text_id, text="¡Listo! Abriendo editor...")
                        self.canvas.coords(self.progress_bar_id, self.bar_x1, self.bar_y, self.bar_x2, self.bar_y + 3)
                        time.sleep(0.4)
                        # Bring main window to front
                        try:
                            win32gui.SetForegroundWindow(ctx["hwnd"])
                        except Exception:
                            pass
                        break
                except Exception:
                    pass
            else:
                if time.time() - start_time > 4.5:
                    break

        self.suppress_legacy_splash = False
        self.close_splash()

    def close_splash(self):
        self.running = False
        try:
            self.root.destroy()
        except Exception:
            pass

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = ShotcutAiSplash()
    app.run()
