# app/ui/tkinter_app.py

import threading
import time
import tkinter as tk
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageTk

from app.config.settings import AppSettings
from app.ui.theme import AppTheme
from app.workflows.register_workflow import RegisterPalmWorkflow
from app.workflows.attendance_workflow import AttendanceWorkflow
from app.services.camera_service import CameraService
from app.services.thermal_service import ThermalService


class PalmTkinterApp:
    def __init__(self, root: tk.Tk, settings: AppSettings):
        self.root = root
        self.settings = settings

        # Use dark theme to match your Flutter dark theme
        self.theme = AppTheme.DARK

        self.current_image = None
        self.is_busy = False

        self.root.title("Palm Scanner")
        self.root.geometry(f"{settings.gui_width}x{settings.gui_height}+0+0")
        self.root.resizable(False, False)
        self.root.configure(bg=self.theme["background_dark"])

        # For 3.5 inch display, hide desktop title bar.
        self.root.overrideredirect(True)

        self._build_ui()

        # Initialize hardware services
        self.camera_service = CameraService(
            width=self.settings.camera_width,
            height=self.settings.camera_height,
            camera_num=self.settings.camera_num,
        )
        self.camera_service.open()
        
        self.thermal_service = ThermalService()

        # Start background loops
        self._camera_loop()
        self._thermal_loop()

    def _create_hover_effect(self, button, normal_bg, hover_bg):
        def on_enter(e):
            if button['state'] != 'disabled':
                button.config(bg=hover_bg)

        def on_leave(e):
            if button['state'] != 'disabled':
                button.config(bg=normal_bg)

        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)

    def _build_ui(self):
        self.main_frame = tk.Frame(
            self.root,
            width=self.settings.gui_width,
            height=self.settings.gui_height,
            bg=self.theme["background"],
        )
        self.main_frame.place(x=0, y=0)

        # Full screen video background
        self.image_label = tk.Label(
            self.main_frame,
            bg=self.theme["surface_dark"],
        )
        self.image_label.place(x=0, y=0, width=self.settings.gui_width, height=self.settings.gui_height)

        # Small Top-Right Controls
        self.exit_button = tk.Button(
            self.main_frame,
            text="×",
            font=("Helvetica", 14, "bold"),
            bg=self.theme["surface"],
            fg=self.theme["text_secondary"],
            activebackground=self.theme["background"],
            activeforeground=self.theme["error"],
            bd=0,
            cursor="hand2",
            command=self.root.destroy,
        )
        self.exit_button.place(x=440, y=5, width=35, height=35)
        self._create_hover_effect(self.exit_button, self.theme["surface"], self.theme["background"])

        self.register_button = tk.Button(
            self.main_frame,
            text="Reg",
            font=("Helvetica", 10, "bold"),
            bg=self.theme["primary"],
            fg="#FFFFFF",
            activebackground=self.theme["primary_dark"],
            activeforeground="#FFFFFF",
            bd=0,
            cursor="hand2",
            command=self.start_register,
        )
        self.register_button.place(x=390, y=5, width=45, height=35)
        self._create_hover_effect(self.register_button, self.theme["primary"], self.theme["primary_dark"])

        # Status text - Overlay at the bottom
        self.status_label = tk.Label(
            self.main_frame,
            text="Ready. Present palm.",
            font=("Helvetica", 12, "bold"),
            fg=self.theme["text_inverse"],
            bg=self.theme["surface_dark"],
            wraplength=440,
            justify="center",
        )
        # Using a slight alpha simulation by using the dark surface color
        self.status_label.place(x=0, y=280, width=480, height=40)

    def set_busy(self, busy: bool):
        self.is_busy = busy
        state = tk.DISABLED if busy else tk.NORMAL
        self.register_button.config(state=state)

        if busy:
            self.register_button.config(bg=self.theme["text_hint"])
        else:
            self.register_button.config(bg=self.theme["primary"])

    def _status_color(self, text: str):
        lower = text.lower()
        if "error" in lower or "failed" in lower:
            return self.theme["error"]
        if "success" in lower or "registered" in lower or "check_in" in lower or "check_out" in lower:
            return self.theme["success"]
        if "waiting" in lower or "scan qr" in lower or "processing" in lower:
            return self.theme["warning"]
        return self.theme["text_inverse"]

    def post_status(self, text: str):
        self.root.after(
            0,
            lambda: self.status_label.config(
                text=text,
                fg=self._status_color(text),
            ),
        )

    def show_error_popup(self, message: str):
        def show():
            popup = tk.Toplevel(self.root)
            popup.title("Error")
            popup.geometry("400x240+40+40")
            popup.configure(bg=self.theme["error"])
            popup.overrideredirect(True)
            popup.attributes('-topmost', True)

            inner = tk.Frame(popup, bg=self.theme["surface"])
            inner.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

            title_lbl = tk.Label(
                inner, text="⚠️ Error Occurred", font=("Helvetica", 14, "bold"),
                fg=self.theme["error"], bg=self.theme["surface"]
            )
            title_lbl.pack(pady=(15, 5))

            msg_lbl = tk.Label(
                inner, text=message, font=("Helvetica", 10),
                fg=self.theme["text_primary"], bg=self.theme["surface"],
                wraplength=360, justify="left", anchor="nw"
            )
            msg_lbl.pack(padx=15, pady=5, fill=tk.BOTH, expand=True)

            btn = tk.Button(
                inner, text="Dismiss", font=("Helvetica", 12, "bold"),
                bg=self.theme["error"], fg="#FFFFFF",
                command=popup.destroy, bd=0, cursor="hand2"
            )
            btn.pack(pady=15, ipadx=20, ipady=5)
            self._create_hover_effect(btn, self.theme["error"], "#DC2626")

        self.root.after(0, show)

    def post_preview(self, frame_bgr: np.ndarray):
        def update():
            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb)
            # Resize to fill the 480x320 screen
            image = image.resize((self.settings.gui_width, self.settings.gui_height))
            self.current_image = ImageTk.PhotoImage(image)
            self.image_label.config(image=self.current_image)
        self.root.after(0, update)

    def post_qr(self, qr_path: Path):
        def update():
            image = Image.open(qr_path).convert("RGB")
            # Enlarge QR code slightly to be readable on full screen
            image = image.resize((240, 240))
            
            # Create a blank dark background and paste QR in center
            bg = Image.new("RGB", (self.settings.gui_width, self.settings.gui_height), (30, 41, 59))
            offset = ((self.settings.gui_width - 240) // 2, (self.settings.gui_height - 240) // 2 - 20)
            bg.paste(image, offset)

            self.current_image = ImageTk.PhotoImage(bg)
            self.image_label.config(image=self.current_image)
        self.root.after(0, update)

    def _camera_loop(self):
        if not self.is_busy:
            try:
                frame = self.camera_service.capture_frame()
                self.post_preview(frame)
            except Exception as e:
                print(f"Camera loop error: {e}")
        
        # ~20 FPS refresh
        self.root.after(50, self._camera_loop)

    def _thermal_loop(self):
        if not self.is_busy:
            max_temp = self.thermal_service.read_max_temp()
            # If a human palm is likely in view
            if max_temp > 33.0:
                print(f"Human detected! Max temp: {max_temp:.1f}C")
                self.start_attendance()
        
        # Poll thermal sensor every 1 second
        self.root.after(1000, self._thermal_loop)

    def run_background(self, target):
        if self.is_busy:
            return

        self.set_busy(True)
        self.post_status("Processing...")

        def wrapper():
            try:
                target()
            except Exception as exc:
                self.post_status("ERROR: Check popup for details")
                self.show_error_popup(str(exc))
            finally:
                # Add a tiny delay before ready to prevent instant re-triggering
                time.sleep(1.0)
                self.root.after(0, lambda: self.set_busy(False))
                self.post_status("Ready. Present palm.")

        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()

    def start_register(self):
        def task():
            workflow = RegisterPalmWorkflow(
                settings=self.settings,
                camera_service=self.camera_service,
                on_status=self.post_status,
                on_preview=self.post_preview,
                on_qr=self.post_qr,
            )
            workflow.run()

        self.run_background(task)

    def start_attendance(self):
        def task():
            workflow = AttendanceWorkflow(
                settings=self.settings,
                camera_service=self.camera_service,
                on_status=self.post_status,
                on_preview=self.post_preview,
            )
            workflow.run()

        self.run_background(task)