# app/ui/tkinter_app.py

import threading
import tkinter as tk
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageTk

from app.config.settings import AppSettings
from app.ui.theme import AppTheme
from app.workflows.register_workflow import RegisterPalmWorkflow
from app.workflows.attendance_workflow import AttendanceWorkflow


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
        self.root.configure(bg=self.theme["background"])

        # For 3.5 inch display, hide desktop title bar.
        # Comment this line if you want normal desktop window.
        self.root.overrideredirect(True)

        self._build_ui()

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

        # Top app bar (sleek header)
        self.app_bar = tk.Frame(
            self.main_frame,
            bg=self.theme["surface"],
            highlightbackground=self.theme["border"],
            highlightthickness=1,
        )
        self.app_bar.place(x=0, y=0, width=480, height=50)

        self.title_label = tk.Label(
            self.app_bar,
            text="Palm Attendance",
            font=("Helvetica", 16, "bold"),
            fg=self.theme["text_primary"],
            bg=self.theme["surface"],
            anchor="w",
        )
        self.title_label.place(x=20, y=10, width=360, height=30)

        self.exit_button = tk.Button(
            self.app_bar,
            text="×",
            font=("Helvetica", 18, "bold"),
            bg=self.theme["surface"],
            fg=self.theme["text_secondary"],
            activebackground=self.theme["background"],
            activeforeground=self.theme["error"],
            bd=0,
            cursor="hand2",
            command=self.root.destroy,
        )
        self.exit_button.place(x=430, y=5, width=40, height=40)
        self._create_hover_effect(self.exit_button, self.theme["surface"], self.theme["background"])

        # Preview card - Bigger and centered
        self.preview_card = tk.Frame(
            self.main_frame,
            bg=self.theme["surface"],
            highlightbackground=self.theme["border"],
            highlightthickness=2,
            bd=0,
        )
        self.preview_card.place(x=60, y=65, width=360, height=160)

        self.image_label = tk.Label(
            self.preview_card,
            bg=self.theme["surface"],
        )
        self.image_label.place(x=5, y=5, width=350, height=150)

        # Status text - Clean and readable
        self.status_label = tk.Label(
            self.main_frame,
            text="Ready",
            font=("Helvetica", 11, "bold"),
            fg=self.theme["text_secondary"],
            bg=self.theme["background"],
            wraplength=440,
            justify="center",
        )
        self.status_label.place(x=20, y=235, width=440, height=25)

        # Buttons - Sleek and dynamic
        self.register_button = tk.Button(
            self.main_frame,
            text="Register",
            font=("Helvetica", 14, "bold"),
            bg=self.theme["primary"],
            fg="#FFFFFF",
            activebackground=self.theme["primary_dark"],
            activeforeground="#FFFFFF",
            bd=0,
            cursor="hand2",
            command=self.start_register,
        )
        self.register_button.place(x=30, y=265, width=200, height=45)
        self._create_hover_effect(self.register_button, self.theme["primary"], self.theme["primary_dark"])

        self.attendance_button = tk.Button(
            self.main_frame,
            text="Check In/Out",
            font=("Helvetica", 14, "bold"),
            bg=self.theme["success"],
            fg="#FFFFFF",
            activebackground="#047857",
            activeforeground="#FFFFFF",
            bd=0,
            cursor="hand2",
            command=self.start_attendance,
        )
        self.attendance_button.place(x=250, y=265, width=200, height=45)
        self._create_hover_effect(self.attendance_button, self.theme["success"], "#047857")

    def set_busy(self, busy: bool):
        self.is_busy = busy

        state = tk.DISABLED if busy else tk.NORMAL

        self.register_button.config(state=state)
        self.attendance_button.config(state=state)

        if busy:
            self.register_button.config(bg=self.theme["text_hint"])
            self.attendance_button.config(bg=self.theme["text_hint"])
        else:
            self.register_button.config(bg=self.theme["primary"])
            self.attendance_button.config(bg=self.theme["success"])

    def post_status(self, text: str):
        self.root.after(
            0,
            lambda: self.status_label.config(
                text=text,
                fg=self._status_color(text),
            ),
        )

    def _status_color(self, text: str):
        lower = text.lower()

        if "error" in lower or "failed" in lower:
            return self.theme["error"]

        if "success" in lower or "registered" in lower or "check_in" in lower or "check_out" in lower:
            return self.theme["success"]

        if "waiting" in lower or "scan qr" in lower or "processing" in lower:
            return self.theme["warning"]

        return self.theme["text_primary"]

    def post_preview(self, frame_bgr: np.ndarray):
        def update():
            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb)

            # Camera preview in 360x160 card
            image = image.resize((350, 150))

            self.current_image = ImageTk.PhotoImage(image)
            self.image_label.config(image=self.current_image)

        self.root.after(0, update)

    def post_qr(self, qr_path: Path):
        def update():
            image = Image.open(qr_path).convert("RGB")

            # QR square centered inside preview card
            image = image.resize((150, 150))

            self.current_image = ImageTk.PhotoImage(image)
            self.image_label.config(image=self.current_image)

        self.root.after(0, update)

    def run_background(self, target):
        if self.is_busy:
            return

        self.set_busy(True)
        self.post_status("Processing...")

        def wrapper():
            try:
                target()
            except Exception as exc:
                self.post_status(f"ERROR:\n{exc}")
            finally:
                self.root.after(0, lambda: self.set_busy(False))

        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()

    def start_register(self):
        def task():
            workflow = RegisterPalmWorkflow(
                settings=self.settings,
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
                on_status=self.post_status,
                on_preview=self.post_preview,
            )
            workflow.run()

        self.run_background(task)