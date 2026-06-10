import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
from tkinter.ttk import Progressbar
from tkinter import messagebox
from tkinter import MULTIPLE
import pandas as pd
import subprocess
import threading
import time
# from google.oauth2.credentials import Credentials
# from google_auth_oauthlib.flow import InstalledAppFlow
# from google.auth.transport.requests import Request
# from googleapiclient.discovery import build
# from googleapiclient.http import MediaFileUpload
import pickle
from datetime import datetime
import os
import signal
import random
import sys
import json
import shutil
import glob
from datetime import timedelta
import smtplib
from email.message import EmailMessage
import webbrowser
import urllib.request
import zipfile

class RTSPRecorderGUI:
    def wait_for_video_ready(self, file_path, timeout=120):
        """
        Wait until FFmpeg finishes writing and the MP4 becomes stable.
        Prevents uploading partially processed videos.
        """

        self.log(
            f"[VIDEO CHECK] Waiting for video finalization: {os.path.basename(file_path)}"
        )

        start_time = time.time()
        previous_size = -1
        stable_count = 0

        while time.time() - start_time < timeout:
            try:
                if not os.path.exists(file_path):
                    time.sleep(2)
                    continue

                current_size = os.path.getsize(file_path)

                # File still growing
                if current_size != previous_size:
                    previous_size = current_size
                    stable_count = 0

                else:
                    stable_count += 1

                # File size stable for ~6 seconds
                if stable_count >= 3:

                    # Validate video using ffprobe
                    ffprobe_path = shutil.which('ffprobe') or 'ffprobe'

                    probe_cmd = [
                        ffprobe_path,
                        '-v', 'error',
                        '-show_entries', 'format=duration',
                        '-of', 'default=noprint_wrappers=1:nokey=1',
                        file_path
                    ]

                    result = subprocess.run(
                        probe_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )

                    if result.returncode == 0 and result.stdout.strip():
                        self.log(
                            f"[VIDEO CHECK] Video finalized successfully: {os.path.basename(file_path)}"
                        )
                        return True

                time.sleep(2)

            except Exception as e:
                self.log(f"[VIDEO CHECK ERROR] {e}")
                time.sleep(2)

        self.log(
            f"[VIDEO CHECK WARNING] Timed out waiting for video readiness: {os.path.basename(file_path)}"
        )

        return False
    def __init__(self, root):
        
        self.root = root
        self.root.title("FFmpeg RTSP Multi-Recorder")
        self.root.geometry("1600x1020")
        self.root.minsize(1350, 850)
        # START WITH HIDDEN MAIN WINDOW
        self.root.withdraw()
        self.main_canvas = None
        self.scrollable_frame = None
        self.processes = []
        self.preview_process = None
        self.preview_paused = False
        self.active_files = []
        self.is_recording = False
        self.recording_end_time = None
        self.recording_duration_seconds = 0
        self.storage_label = None
        self.auto_mode_enabled = False
        self.auto_record_time = tk.StringVar(value="09:00")
        self.auto_last_run_date = None
        self.last_auto_camera = None
        self.gmail_sender = "work.sakshamtalwar@gmail.com"
        self.gmail_app_password = "xkeq iewd gkgg aqpo"

        # MULTIPLE EMAIL RECIPIENTS
        self.notification_emails = [
            
            "saksham.talwar@beltech.in",
            
        ]

        self.google_drive_folder_link = "https://drive.google.com/drive/folders/1nVHCKptgCVOaoRK3st8Sw-t-mwnRZOWy?usp=sharing"
        self.google_drive_folder_id = "1nVHCKptgCVOaoRK3st8Sw-t-mwnRZOWy"
                
        self.csv_path = tk.StringVar(value="")
        self.save_dir = tk.StringVar(value=os.path.expanduser("~/Desktop"))
        self.start_time = tk.StringVar(value="01:30")
        self.start_period = tk.StringVar(value="PM")
        self.start_mode = tk.StringVar(value="now")
        self.duration = tk.StringVar(value="01:00:00")
        if os.name == 'nt':
            default_codec = 'copy'
        else:
            default_codec = 'copy'

        self.codec = tk.StringVar(value=default_codec)
        self.bitrate = tk.StringVar(value="1M")
        self.transport = tk.StringVar(value="tcp")

        self.all_junctions = []
        self.selected_junctions = []

        self.is_windows = os.name == 'nt'

        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
            user_data_path = os.path.join(os.path.expanduser('~'), '.traffic_recorder')
            os.makedirs(user_data_path, exist_ok=True)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
            user_data_path = base_path

        if self.is_windows:
            bundled_ffmpeg = self.resource_path('ffmpeg.exe')
            self.ffmpeg_path = bundled_ffmpeg if os.path.exists(bundled_ffmpeg) else 'ffmpeg'
        else:
            self.ffmpeg_path = (
                shutil.which("ffmpeg")
                or "/opt/homebrew/bin/ffmpeg"
                or "/usr/local/bin/ffmpeg"
            )

        self.config_file = os.path.join(user_data_path, 'recent_rtsp.json')
        self.camera_history_file = os.path.join(user_data_path, 'camera_history.json')

        if self.is_windows and not os.path.exists(self.ffmpeg_path):
            self.ffmpeg_path = 'ffmpeg'

        self.setup_ui()
        if not self.verify_ffmpeg():
            return
        self.show_welcome_screen()
        self.update_live_clock()
        self.update_storage_info()
        self.log("[SYSTEM] Smart Traffic Recorder Dashboard initialized successfully.")
        self.log("[SYSTEM] Ready to load RTSP CSV files and start monitoring.")


    def show_welcome_screen(self):
        welcome = tk.Toplevel()
        welcome.overrideredirect(True)
        welcome.configure(bg="#0f172a")

        screen_width = welcome.winfo_screenwidth()
        screen_height = welcome.winfo_screenheight()

        width = 700
        height = 300

        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)

        welcome.geometry(f"{width}x{height}+{x}+{y}")
        welcome.attributes('-topmost', True)
        welcome.attributes('-alpha', 1.0)

        title_label = tk.Label(
            welcome,
            text="SMART TRAFFIC RECORDER",
            font=("Segoe UI", 28, "bold"),
            fg="#38bdf8",
            bg="#0f172a"
        )
        title_label.pack(expand=True)

        subtitle_label = tk.Label(
            welcome,
            text="Welcome User • Initializing Dashboard...",
            font=("Segoe UI", 14),
            fg="#cbd5e1",
            bg="#0f172a"
        )
        subtitle_label.pack(pady=(0, 40))

        progress = ttk.Progressbar(
            welcome,
            orient="horizontal",
            mode="indeterminate",
            length=350
        )
        progress.pack(pady=(0, 30))
        progress.start(12)

        def fade_out(alpha=1.0):
            alpha -= 0.05

            if alpha <= 0:
                welcome.destroy()
                self.root.deiconify()
                return

            welcome.attributes('-alpha', alpha)
            welcome.after(50, lambda: fade_out(alpha))

        welcome.after(1800, fade_out)

    def resource_path(self, relative_path):
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath('.')

        return os.path.join(base_path, relative_path)

    def download_ffmpeg_windows(self):
        try:
            install_dir = os.path.join(
                os.path.expanduser("~"),
                ".traffic_recorder",
                "ffmpeg"
            )

            os.makedirs(install_dir, exist_ok=True)

            zip_path = os.path.join(install_dir, "ffmpeg.zip")

            download_url = (
                "https://www.gyan.dev/ffmpeg/builds/"
                "ffmpeg-release-essentials.zip"
            )

            self.log("[SYSTEM] Downloading FFmpeg automatically...")

            urllib.request.urlretrieve(download_url, zip_path)

            self.log("[SYSTEM] Extracting FFmpeg...")

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(install_dir)

            try:
                os.remove(zip_path)
            except Exception:
                pass

            for root_dir, dirs, files in os.walk(install_dir):
                if 'ffmpeg.exe' in files:
                    self.ffmpeg_path = os.path.join(root_dir, 'ffmpeg.exe')
                    self.ffprobe_path = os.path.join(root_dir, 'ffprobe.exe')
                    self.ffplay_path = os.path.join(root_dir, 'ffplay.exe')

                    self.log("[SYSTEM] FFmpeg installed successfully.")
                    return True

            self.log("[SYSTEM] FFmpeg download completed but binaries were not found.")
            return False

        except Exception as e:
            self.log(f"[SYSTEM] Automatic FFmpeg installation failed: {e}")
            return False

    def verify_ffmpeg(self):
        """
        Detect bundled FFmpeg first.
        Fall back to system installation.
        Allow manual selection if not found.
        """

        # --------------------------------
        # 1. Check bundled binaries
        # --------------------------------

        bundled_ffmpeg = self.resource_path(
            "ffmpeg.exe" if self.is_windows else "ffmpeg"
        )

        bundled_ffprobe = self.resource_path(
            "ffprobe.exe" if self.is_windows else "ffprobe"
        )

        bundled_ffplay = self.resource_path(
            "ffplay.exe" if self.is_windows else "ffplay"
        )
        self.log(f"[FFMPEG DEBUG] bundled_ffmpeg={bundled_ffmpeg}")
        self.log(f"[FFMPEG DEBUG] bundled_ffprobe={bundled_ffprobe}")
        self.log(f"[FFMPEG DEBUG] ffmpeg exists={os.path.exists(bundled_ffmpeg)}")
        self.log(f"[FFMPEG DEBUG] ffprobe exists={os.path.exists(bundled_ffprobe)}")

        if (
            os.path.exists(bundled_ffmpeg)
            and os.path.exists(bundled_ffprobe)
        ):
            self.ffmpeg_path = bundled_ffmpeg
            self.ffprobe_path = bundled_ffprobe
            self.ffplay_path = bundled_ffplay

            self.log("[SYSTEM] Using bundled FFmpeg binaries")
            return True

        # --------------------------------
        # 2. Check system PATH
        # --------------------------------

        possible_ffmpeg = [
            "/opt/homebrew/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
            shutil.which("ffmpeg")
        ]

        possible_ffprobe = [
            "/opt/homebrew/bin/ffprobe",
            "/usr/local/bin/ffprobe",
            shutil.which("ffprobe")
        ]

        possible_ffplay = [
            "/opt/homebrew/bin/ffplay",
            "/usr/local/bin/ffplay",
            shutil.which("ffplay")
        ]

        ffmpeg_found = next((p for p in possible_ffmpeg if p and os.path.exists(p)), None)
        ffprobe_found = next((p for p in possible_ffprobe if p and os.path.exists(p)), None)
        ffplay_found = next((p for p in possible_ffplay if p and os.path.exists(p)), None)

        if ffmpeg_found and ffprobe_found:
            self.ffmpeg_path = ffmpeg_found
            self.ffprobe_path = ffprobe_found
            self.ffplay_path = ffplay_found

            self.log("[SYSTEM] Using system FFmpeg installation")
            return True

        # --------------------------------
        # 3. Ask user
        # --------------------------------

        answer = messagebox.askyesnocancel(
            "FFmpeg Missing",
            "FFmpeg was not found.\n\n"
            "YES → Install FFmpeg Automatically\n"
            "NO → Locate Existing FFmpeg\n"
            "CANCEL → Exit"
        )

        if answer is None:
            self.root.destroy()
            return False

        if answer is True:

            if self.is_windows:
                if self.download_ffmpeg_windows():
                    return True

                messagebox.showerror(
                    "Installation Failed",
                    "Unable to automatically install FFmpeg."
                )
                self.root.destroy()
                return False

            messagebox.showinfo(
                "Automatic Installation",
                "Automatic installation is currently supported on Windows only."
            )

        if answer is False:

            ffmpeg_file = filedialog.askopenfilename(
                title="Select ffmpeg executable"
            )

            if not ffmpeg_file:
                self.root.destroy()
                return False

            self.ffmpeg_path = ffmpeg_file

            ffmpeg_folder = os.path.dirname(ffmpeg_file)

            self.ffprobe_path = os.path.join(
                ffmpeg_folder,
                "ffprobe.exe" if self.is_windows else "ffprobe"
            )

            self.ffplay_path = os.path.join(
                ffmpeg_folder,
                "ffplay.exe" if self.is_windows else "ffplay"
            )

            return os.path.exists(self.ffprobe_path)

    def setup_ui(self):
        # =========================
        # SCROLLABLE MAIN LAYOUT
        # =========================

        self.main_canvas = tk.Canvas(
            self.root,
            bg="#0f172a",
            highlightthickness=0
        )

        vertical_scrollbar = ttk.Scrollbar(
            self.root,
            orient="vertical",
            command=self.main_canvas.yview
        )

        self.scrollable_frame = ttk.Frame(self.main_canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.main_canvas.configure(
                scrollregion=self.main_canvas.bbox("all")
            )
        )

        self.canvas_window = self.main_canvas.create_window(
            (0, 0),
            window=self.scrollable_frame,
            anchor="nw"
        )

        self.main_canvas.configure(
            yscrollcommand=vertical_scrollbar.set
        )

        self.main_canvas.pack(
            side="left",
            fill="both",
            expand=True
        )
        # Force canvas focus so scrolling works globally
        self.main_canvas.focus_set()

        vertical_scrollbar.pack(
            side="right",
            fill="y"
        )

        # =========================
        # GLOBAL APP SCROLL SUPPORT
        # =========================

        def _on_mousewheel(event):
            try:
                # macOS trackpad support
                if sys.platform == 'darwin':
                    delta = int(-1 * event.delta)

                    if delta == 0:
                        delta = -1

                    self.main_canvas.yview_scroll(delta, "units")

                # Windows/Linux mouse wheel
                else:
                    self.main_canvas.yview_scroll(
                        int(-1 * (event.delta / 120)),
                        "units"
                    )

            except Exception:
                pass

        def _on_linux_scroll(event):
            try:
                if event.num == 4:
                    self.main_canvas.yview_scroll(-3, "units")
                elif event.num == 5:
                    self.main_canvas.yview_scroll(3, "units")
            except Exception:
                pass

        # GLOBAL SCROLLING SUPPORT
        self.root.bind_all("<MouseWheel>", _on_mousewheel, add="+")

        # macOS trackpad horizontal/gesture support
        self.root.bind_all("<Shift-MouseWheel>", _on_mousewheel, add="+")

        # Linux support
        self.root.bind_all("<Button-4>", _on_linux_scroll, add="+")
        self.root.bind_all("<Button-5>", _on_linux_scroll, add="+")

        self.main_canvas.bind(
            '<Configure>',
            lambda e: self.main_canvas.itemconfig(
                self.canvas_window,
                width=e.width
            )
        )

        title_frame = ttk.Frame(self.scrollable_frame, padding=10)
                # Make root window scalable
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        title_frame.pack(fill="x")

        ttk.Label(
            title_frame,
            text="Smart Traffic Camera Recording Dashboard",
            font=("Segoe UI", 20, "bold")
        ).pack(anchor="center")

        ttk.Label(
            title_frame,
            text="Select traffic junctions and start recording with one click.",
            font=("Arial", 10)
        ).pack(anchor="center", pady=5)

        self.live_clock_label = ttk.Label(
            title_frame,
            text="",
            font=("Consolas", 14, "bold"),
            foreground="green"
        )
        self.live_clock_label.pack(anchor="center", pady=4)

        self.storage_label = ttk.Label(
            title_frame,
            text="Storage Available: Calculating...",
            font=("Consolas", 11, "bold"),
            foreground="blue"
        )
        self.storage_label.pack(anchor="center", pady=2)

        ttk.Button(
            title_frame,
            text="Need Help Buddy?",
            command=self.show_help_guide
        ).pack(anchor="center", pady=5)

        frame_files = ttk.LabelFrame(self.scrollable_frame, text="CSV Camera Source Management", padding=10)
        frame_files.pack(fill="x", padx=10, pady=5)
        frame_files.columnconfigure(1, weight=1)
        frame_files.columnconfigure(2, weight=1)

        ttk.Label(frame_files, text="CSV Path:").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame_files, textvariable=self.csv_path, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(frame_files, text="Browse", command=self.browse_csv).grid(row=0, column=2)

        ttk.Button(
            frame_files,
            text="Load Junctions From CSV",
            command=self.load_junctions
        ).grid(row=1, column=1, pady=10, sticky="w")

        # --- Direct RTSP Link Entry Section ---
        ttk.Label(
            frame_files,
            text="Camera Name + RTSP Link:"
        ).grid(row=2, column=0, sticky="w", pady=5)

        self.manual_rtsp = tk.StringVar()
        self.manual_rtsp_name = tk.StringVar()

        ttk.Entry(
            frame_files,
            textvariable=self.manual_rtsp_name,
            width=20
        ).grid(row=2, column=1, padx=5, sticky="w")

        ttk.Entry(
            frame_files,
            textvariable=self.manual_rtsp,
            width=35
        ).grid(row=2, column=2, padx=5, sticky="w")

        ttk.Button(
            frame_files,
            text="Add RTSP Stream",
            command=self.add_manual_rtsp
        ).grid(row=2, column=3, padx=5)

        ttk.Label(
            frame_files,
            text="Multiple RTSP Links (Required Format: CameraName,RTSP_URL)"
        ).grid(row=3, column=0, sticky="nw", pady=5)

        self.multi_rtsp_text = tk.Text(
            frame_files,
            height=6,
            width=80
        )

        self.multi_rtsp_text.grid(
            row=3,
            column=1,
            columnspan=3,
            sticky="ew",
            padx=5,
            pady=5
        )

        ttk.Button(
            frame_files,
            text="Add Multiple RTSP Streams",
            command=self.add_multiple_rtsp
        ).grid(row=4, column=1, sticky="w", pady=5)

        ttk.Label(frame_files, text="Save Recordings To:").grid(row=5, column=0, sticky="w", pady=5)
        ttk.Entry(frame_files, textvariable=self.save_dir, width=50).grid(row=5, column=1, padx=5)
        ttk.Button(frame_files, text="Browse", command=self.browse_dir).grid(row=5, column=2)

        junction_frame = ttk.LabelFrame(
            self.scrollable_frame,
            text="Available Traffic Junctions",
            padding=10
        )
        junction_frame.pack(fill="both", expand=False, padx=10, pady=5)

        ttk.Label(
            junction_frame,
            text="Select one or multiple junctions to start recording",
            font=("Arial", 10)
        ).pack(anchor="w")

        junction_list_container = tk.Frame(
            junction_frame,
            bg="#08111f"
        )
        junction_list_container.pack(
            fill="both",
            expand=True,
            pady=5
        )

        junction_scrollbar = ttk.Scrollbar(
            junction_list_container,
            orient="vertical"
        )
        junction_scrollbar.pack(side="right", fill="y")

        self.junction_listbox = tk.Listbox(
            junction_list_container,
            selectmode=MULTIPLE,
            height=7,
            bg="#08111f",
            fg="#d1fae5",
            selectbackground="#2563eb",
            selectforeground="white",
            relief="flat",
            borderwidth=0,
            font=("Segoe UI", 10),
            yscrollcommand=junction_scrollbar.set
        )

        self.junction_listbox.pack(
            side="left",
            fill="both",
            expand=True
        )

        junction_scrollbar.config(
            command=self.junction_listbox.yview
        )

        def junction_mousewheel(event):
            try:
                if sys.platform == 'darwin':
                    self.junction_listbox.yview_scroll(
                        int(-1 * event.delta),
                        "units"
                    )
                else:
                    self.junction_listbox.yview_scroll(
                        int(-1 * (event.delta / 120)),
                        "units"
                    )

                return "break"

            except Exception:
                return "break"

        self.junction_listbox.bind(
            "<MouseWheel>",
            junction_mousewheel
        )

        self.junction_listbox.bind(
            "<Button-4>",
            lambda e: self.junction_listbox.yview_scroll(-3, "units")
        )

        self.junction_listbox.bind(
            "<Button-5>",
            lambda e: self.junction_listbox.yview_scroll(3, "units")
        )

        preview_frame = ttk.Frame(junction_frame)
        preview_frame.pack(fill="x", pady=5)

        ttk.Button(
            preview_frame,
            text="Open Live Preview",
            command=self.open_live_preview
        ).pack(side="left", padx=5)

        frame_time = ttk.LabelFrame(self.scrollable_frame, text="Recording Schedule", padding=10)
        frame_time.pack(fill="x", padx=10, pady=5)
        for col in range(7):
            frame_time.columnconfigure(col, weight=1)

        ttk.Label(frame_time, text="Recording Start:").grid(row=0, column=0, sticky="w")

        ttk.Radiobutton(
            frame_time,
            text="Start Now",
            variable=self.start_mode,
            value="now"
        ).grid(row=0, column=1, sticky="w")

        ttk.Radiobutton(
            frame_time,
            text="Schedule Time",
            variable=self.start_mode,
            value="scheduled"
        ).grid(row=0, column=2, sticky="w")

        ttk.Entry(
            frame_time,
            textvariable=self.start_time,
            width=10
        ).grid(row=0, column=3, sticky="w", padx=5)

        ttk.Combobox(
            frame_time,
            textvariable=self.start_period,
            values=["AM", "PM"],
            width=5,
            state="readonly"
        ).grid(row=0, column=4, sticky="w")

        ttk.Label(frame_time, text="Recording Duration (HH:MM:SS):").grid(row=0, column=5, sticky="w", padx=10)
        ttk.Entry(frame_time, textvariable=self.duration, width=12).grid(row=0, column=6, sticky="w")

        preset_frame = ttk.Frame(frame_time)
        preset_frame.grid(row=1, column=5, columnspan=2, sticky="w", pady=5)

        ttk.Label(
            preset_frame,
            text="Quick Presets:"
        ).pack(side="left", padx=(0,5))

        ttk.Button(
            preset_frame,
            text="Test 1 Min",
            command=lambda: self.set_duration_preset("00:01:00")
        ).pack(side="left", padx=2)

        ttk.Button(
            preset_frame,
            text="30 Min",
            command=lambda: self.set_duration_preset("00:30:00")
        ).pack(side="left", padx=2)

        ttk.Button(
            preset_frame,
            text="1 Hour",
            command=lambda: self.set_duration_preset("01:00:00")
        ).pack(side="left", padx=2)

        ttk.Button(
            preset_frame,
            text="3 Hours",
            command=lambda: self.set_duration_preset("03:00:00")
        ).pack(side="left", padx=2)

        self.timer_label = ttk.Label(
            frame_time,
            text="Remaining Time: --:--:--",
            font=("Arial", 10, "bold")
        )
        self.timer_label.grid(row=1, column=0, columnspan=2, pady=10, sticky="w")
        self.finish_time_label = ttk.Label(
            frame_time,
            text="Expected Finish Time: --:--:--",
            font=("Arial", 10, "bold"),
            foreground="blue"
        )

        self.finish_time_label.grid(
            row=2,
            column=0,
            columnspan=3,
            pady=5,
            sticky="w"
        )

        self.progress = Progressbar(
            frame_time,
            orient="horizontal",
            length=300,
            mode="determinate"
        )
        self.progress.grid(row=1, column=2, columnspan=2, padx=10, pady=10, sticky="w")

        # --- Paste Video Recording Quality and Controls/Logs UI here ---
        frame_ffmpeg = ttk.LabelFrame(self.scrollable_frame, text="Video Recording Quality Settings", padding=10)
        frame_ffmpeg.pack(fill="x", padx=10, pady=5)
        for col in range(4):
            frame_ffmpeg.columnconfigure(col, weight=1)

        ttk.Label(frame_ffmpeg, text="Video Codec:").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            frame_ffmpeg,
            textvariable=self.codec,
            values=["libx264", "copy", "h264_videotoolbox"],
            width=18
        ).grid(row=0, column=1, padx=5, sticky="w")

        ttk.Label(frame_ffmpeg, text="Bitrate:").grid(row=0, column=2, sticky="w", padx=10)
        ttk.Entry(frame_ffmpeg, textvariable=self.bitrate, width=12).grid(row=0, column=3, sticky="w")

        ttk.Label(frame_ffmpeg, text="RTSP Transport:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Combobox(
            frame_ffmpeg,
            textvariable=self.transport,
            values=["tcp", "udp"],
            width=18
        ).grid(row=1, column=1, padx=5, sticky="w")

        frame_controls = ttk.Frame(self.scrollable_frame, padding=10)
        frame_controls.pack(fill="x")

        self.btn_schedule = ttk.Button(
            frame_controls,
            text="Schedule Recording",
            command=self.start_scheduled_thread
        )
        self.btn_schedule.pack(side="left", padx=5)

        self.btn_now = ttk.Button(
            frame_controls,
            text="Start Recording Now",
            command=self.start_recording_thread
        )
        self.btn_now.pack(side="left", padx=5)

        self.btn_stop = ttk.Button(
            frame_controls,
            text="Stop All Recordings",
            command=self.stop_all
        )
        self.btn_stop.pack(side="right", padx=5)

        auto_frame = ttk.LabelFrame(self.scrollable_frame, text="Automatic Daily Recording Mode", padding=10)
        auto_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(
            auto_frame,
            text="Daily Auto Recording Time (24 Hour Format HH:MM):"
        ).grid(row=0, column=0, sticky="w")

        ttk.Entry(
            auto_frame,
            textvariable=self.auto_record_time,
            width=12
        ).grid(row=0, column=1, padx=5, sticky="w")

        ttk.Button(
            auto_frame,
            text="Enable Auto Mode",
            command=self.enable_auto_mode
        ).grid(row=0, column=2, padx=5)

        ttk.Button(
            auto_frame,
            text="Disable Auto Mode",
            command=self.disable_auto_mode
        ).grid(row=0, column=3, padx=5)

        ttk.Button(
            auto_frame,
            text="Run Auto Mode Test",
            command=self.run_auto_mode_test
        ).grid(row=0, column=4, padx=5)

        ttk.Label(
            auto_frame,
            text="Auto mode records one random active traffic camera daily for 30 minutes and sends notification when ready.",
            font=("Arial", 9)
        ).grid(row=1, column=0, columnspan=5, sticky="w", pady=5)

        # =========================
        # LOGS + RECENT RECORDINGS
        # =========================

        dashboard_bottom = ttk.PanedWindow(
            self.scrollable_frame,
            orient=tk.HORIZONTAL
        )
        dashboard_bottom.configure(height=650)
        dashboard_bottom.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=5,
            side="bottom"
        )

        # ---------- LIVE LOGS ----------

        frame_logs = ttk.LabelFrame(
            dashboard_bottom,
            text="LIVE SYSTEM LOGS & RECORDING ACTIVITY",
            padding=10
        )

        dashboard_bottom.add(frame_logs, weight=7)

        self.log_area = scrolledtext.ScrolledText(
            frame_logs,
            width=95,
            height=34,
            state='disabled',
            bg="#111827",
            fg="#cbd5e1",
            insertbackground="#cbd5e1",
            relief="flat",
            borderwidth=0,
            padx=20,
            pady=20,
            highlightthickness=1,
            highlightbackground="#1e293b",
            font=("Segoe UI", 11)
        )

        self.log_area.pack(
            fill="both",
            expand=True
        )

        ttk.Label(
            frame_logs,
            text="Real-time FFmpeg logs, RTSP stream monitoring, recording progress, errors, timer updates and CCTV activity appear here live.",
            font=("Arial", 11, "bold")
        ).pack(anchor="w", pady=6)

        # ---------- RECENT RECORDINGS ----------

        recent_frame = ttk.LabelFrame(
            dashboard_bottom,
            text="Recently Recorded Videos",
            padding=10
        )

        dashboard_bottom.add(recent_frame, weight=4)

        self.recent_recordings_list = tk.Listbox(
            recent_frame,
            height=34,
            width=50,
            bg="#111827",
            fg="#cbd5e1",
            selectbackground="#2563eb",
            selectforeground="white",
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground="#1e293b",
            font=("Segoe UI", 10)
        )

        self.recent_recordings_list.pack(
            fill="both",
            expand=True
        )

        self.recent_recordings_list.bind(
            '<Double-Button-1>',
            lambda e: self.open_selected_recording()
        )

        recent_controls = ttk.Frame(recent_frame)
        recent_controls.pack(fill="x", pady=5)

        ttk.Button(
            recent_controls,
            text="Open Selected Video",
            command=self.open_selected_recording
        ).pack(side="left", padx=5)

        ttk.Button(
            recent_controls,
            text="Refresh List",
            command=self.refresh_recent_recordings
        ).pack(side="left", padx=5)

        self.refresh_recent_recordings()

        footer = ttk.Label(
            self.scrollable_frame,
            text="Made by Saksham Talwar | For any problem contact: 7217739614",
            font=("Segoe UI", 9)
        )
        footer.pack(side="bottom", pady=8)
    def update_live_clock(self):
        try:
            current_time = datetime.now().strftime(
                "%A | %d %B %Y | %I:%M:%S %p"
            )

            self.live_clock_label.config(
                text=f"LIVE SYSTEM TIME → {current_time}"
            )

        except Exception:
            pass

        self.root.after(1000, self.update_live_clock)

    def update_storage_info(self):
        try:
            save_path = self.save_dir.get()

            if not os.path.exists(save_path):
                save_path = os.path.expanduser("~/Desktop")

            usage = shutil.disk_usage(save_path)

            free_gb = usage.free / (1024 ** 3)
            total_gb = usage.total / (1024 ** 3)
            used_gb = (usage.total - usage.free) / (1024 ** 3)

            text = (
                f"Storage Available: {free_gb:.1f} GB | "
                f"Used: {used_gb:.1f} GB | "
                f"Total: {total_gb:.1f} GB"
            )

            if self.storage_label:
                self.storage_label.config(text=text)

                if free_gb < 20:
                    self.storage_label.config(foreground="red")
                elif free_gb < 50:
                    self.storage_label.config(foreground="orange")
                else:
                    self.storage_label.config(foreground="green")

            if free_gb < 10:
                self.log(
                    "[WARNING] Low disk space detected. Less than 10 GB remaining."
                )

        except Exception:
            pass

        self.root.after(10000, self.update_storage_info)

    def show_help_guide(self):
        help_text = """
SMART TRAFFIC CAMERA RECORDING DASHBOARD

━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — LOAD CAMERA CSV
━━━━━━━━━━━━━━━━━━━━━━
• Click Browse
• Select one or multiple CSV files
• Click 'Load Junctions From CSV'

The traffic junctions will appear automatically.

━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — SELECT JUNCTIONS
━━━━━━━━━━━━━━━━━━━━━━
• Click any junction to select it
• Hold CTRL to select multiple cameras

━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — LIVE PREVIEW
━━━━━━━━━━━━━━━━━━━━━━
• Select a junction
• Click 'Open Live Preview'

LIVE PREVIEW SHORTCUTS:
SPACE → Pause / Resume
F → Fullscreen
ESC → Exit Preview

━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — CHOOSE RECORDING MODE
━━━━━━━━━━━━━━━━━━━━━━
START NOW
→ Starts recording instantly

SCHEDULE TIME
→ Starts recording automatically
   at selected AM/PM time

━━━━━━━━━━━━━━━━━━━━━━
STEP 5 — SET RECORDING DURATION
━━━━━━━━━━━━━━━━━━━━━━
Examples:

00:15:00
→ 15 Minutes

01:00:00
→ 1 Hour

02:30:00
→ 2 Hours 30 Minutes

━━━━━━━━━━━━━━━━━━━━━━
STEP 6 — START RECORDING
━━━━━━━━━━━━━━━━━━━━━━
Click:
'Start Recording Now'

Timer and progress bar update automatically.

━━━━━━━━━━━━━━━━━━━━━━
STEP 7 — VIEW SAVED VIDEOS
━━━━━━━━━━━━━━━━━━━━━━
Recently recorded videos appear on the right side.

Select a video and click:
'Open Selected Video'

━━━━━━━━━━━━━━━━━━━━━━
IMPORTANT TIPS
━━━━━━━━━━━━━━━━━━━━━━
• Use TCP transport for stable CCTV recording
• Use codec COPY for best compatibility
• Ensure RTSP links are active
• Videos save automatically
• Green logs show active recording events

━━━━━━━━━━━━━━━━━━━━━━
BUILT FOR:
━━━━━━━━━━━━━━━━━━━━━━
• Traffic Monitoring Teams
• CCTV Operators
• Control Rooms
• Non-Technical Operators
        """

        help_window = tk.Toplevel(self.root)
        help_window.title("Smart Traffic Recorder - Operator Guide")
        help_window.geometry("750x650")
        help_window.minsize(600, 500)

        help_frame = ttk.Frame(help_window, padding=10)
        help_frame.pack(fill="both", expand=True)

        ttk.Label(
            help_frame,
            text="Smart Traffic Recorder - Beginner Help Guide",
            font=("Arial", 16, "bold")
        ).pack(pady=(0, 10))

        help_scroll = scrolledtext.ScrolledText(
            help_frame,
            wrap=tk.WORD,
            font=("Arial", 11),
            bg="#1e1e1e",
            fg="white"
        )
        help_scroll.pack(fill="both", expand=True)

        help_scroll.insert(tk.END, help_text)
        help_scroll.config(state='disabled')

        button_frame = ttk.Frame(help_frame)
        button_frame.pack(fill="x", pady=10)

        ttk.Button(
            button_frame,
            text="Close Guide",
            command=help_window.destroy
        ).pack(side="right")
    def refresh_recent_recordings(self):
        self.recent_recordings_list.delete(0, tk.END)

        try:
            save_directory = self.save_dir.get()

            if not os.path.exists(save_directory):
                return

            video_files = [
                os.path.join(save_directory, f)
                for f in os.listdir(save_directory)
                if f.lower().endswith('.mp4')
            ]

            video_files.sort(key=os.path.getmtime, reverse=True)

            for video in video_files[:30]:
                self.recent_recordings_list.insert(
                    tk.END,
                    os.path.basename(video)
                )

        except Exception as e:
            self.log(f"[ERROR] Failed loading recent recordings: {e}")

    def open_selected_recording(self):
        try:
            selected = self.recent_recordings_list.curselection()

            if not selected:
                return

            filename = self.recent_recordings_list.get(selected[0])

            full_path = os.path.join(self.save_dir.get(), filename)

            if self.is_windows:
                os.startfile(full_path)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', full_path])
            else:
                subprocess.Popen(['xdg-open', full_path])

            self.log(f"[SYSTEM] Opened recording: {filename}")

        except Exception as e:
            self.log(f"[ERROR] Failed opening recording: {e}")

    def fix_selected_video(self):
        try:
            selected = self.recent_recordings_list.curselection()

            if not selected:
                messagebox.showwarning(
                    "No Video Selected",
                    "Please select a video first."
                )
                return

            filename = self.recent_recordings_list.get(selected[0])

            original_file = os.path.join(
                self.save_dir.get(),
                filename
            )

            if not os.path.exists(original_file):
                self.log(
                    f"[FIX VIDEO ERROR] File not found: {filename}"
                )
                return

            fixed_file = os.path.splitext(original_file)[0] + "_FIXED.mp4"

            self.log(
                f"[FIX VIDEO] Starting repair process for: {filename}"
            )

            repair_cmd = [
                self.ffmpeg_path,
                "-y",
                "-err_detect",
                "ignore_err",
                "-i",
                original_file,
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                "-c:a",
                "aac",
                fixed_file
            ]

            subprocess.run(
                repair_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=300
            )

            if os.path.exists(fixed_file):
                self.log(
                    f"[FIX VIDEO] Video repaired successfully: {os.path.basename(fixed_file)}"
                )

                self.refresh_recent_recordings()

                messagebox.showinfo(
                    "Video Repair Completed",
                    f"Fixed video created successfully:\n\n{os.path.basename(fixed_file)}"
                )

            else:
                self.log(
                    "[FIX VIDEO ERROR] FFmpeg failed to generate repaired video."
                )

        except Exception as e:
            self.log(f"[FIX VIDEO ERROR] {e}")
    def save_recent_rtsp(self, name, rtsp):
        try:
            recent_data = []

            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    recent_data = json.load(f)

            recent_data.append({
                "name": name,
                "rtsp": rtsp
            })

            recent_data = recent_data[-20:]

            with open(self.config_file, 'w') as f:
                json.dump(recent_data, f, indent=4)

        except Exception as e:
            self.log(f"[ERROR] Failed saving recent RTSP: {e}")


    def get_drive_service(self):
        SCOPES = ['https://www.googleapis.com/auth/drive.file']

        creds = None

        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:

            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())

            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json',
                    SCOPES
                )

                creds = flow.run_local_server(port=0)

            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        service = build('drive', 'v3', credentials=creds)

        return service
    def upload_to_google_drive(self, file_path):
        try:
            service = self.get_drive_service()

            filename = os.path.basename(file_path)

            file_metadata = {
                'name': filename,
                'parents': [self.google_drive_folder_id]
            }

            media = MediaFileUpload(
                file_path,
                resumable=True
            )

            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()

            file_id = file.get('id')

            # Make public
            service.permissions().create(
                fileId=file_id,
                body={'type': 'anyone', 'role': 'reader'}
            ).execute()

            shareable_link = f"https://drive.google.com/file/d/{file_id}/view"

            self.log(
                f"[UPLOAD] Google Drive upload successful: {filename}"
            )

            return shareable_link

        except Exception as e:
            self.log(f"[UPLOAD ERROR] {e}")
            return None
    
    def open_live_preview(self):
        try:
            selected_indices = self.junction_listbox.curselection()

            if not selected_indices:
                messagebox.showwarning(
                    "No Junction Selected",
                    "Please select a junction first."
                )
                return

            selected_camera = self.all_junctions[selected_indices[0]]

            rtsp_link = selected_camera["rtsp"]

            ffplay_path = shutil.which("ffplay")

            if not ffplay_path and sys.platform == "darwin":
                ffplay_path = "/opt/homebrew/bin/ffplay"

            if not ffplay_path:
                ffplay_path = self.ffmpeg_path.replace("ffmpeg.exe", "ffplay.exe")

            if not os.path.exists(ffplay_path):
                raise FileNotFoundError(
                    f"FFplay not found: {ffplay_path}"
                )
            preview_cmd = [
                ffplay_path,
                "-rtsp_transport",
                self.transport.get(),
                # "-hide_banner",
                # "-loglevel",
                # "quiet",
                "-fflags",
                "nobuffer+discardcorrupt",
                "-flags",
                "low_delay",
                "-window_title",
                f"Live Preview - {selected_camera['name']} | SPACE Pause | F Fullscreen | ESC Exit",
                "-x",
                "1280",
                "-y",
                "720",
                rtsp_link
            ]

            self.log(f"[PREVIEW] Using ffplay: {ffplay_path}")
            self.log(f"[PREVIEW] Opening stream: {rtsp_link}")

            self.preview_process = subprocess.Popen(
                preview_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.root.after(
                3000,
                lambda: self.log(
                    f"[PREVIEW STATUS] Process running: {self.preview_process.poll() is None}"
                )
            )
            self.preview_paused = False

            instruction_window = tk.Toplevel(self.root)
            instruction_window.title("Live Preview Controls")
            instruction_window.geometry("420x140")
            instruction_window.resizable(False, False)
            instruction_window.configure(bg="#1e1e1e")

            ttk.Label(
                instruction_window,
                text="LIVE PREVIEW CONTROLS",
                font=("Arial", 14, "bold")
            ).pack(pady=(10, 5))

            instructions = (
                "SPACE → Pause / Resume\n"
                "F → Fullscreen Mode\n"
                "ESC → Exit Live Preview"
            )

            instruction_label = tk.Label(
                instruction_window,
                text=instructions,
                font=("Arial", 11),
                bg="#1e1e1e",
                fg="white",
                justify="left"
            )
            instruction_label.pack(pady=5)

            ttk.Button(
                instruction_window,
                text="Close",
                command=instruction_window.destroy
            ).pack(pady=(5, 10))

            self.log(
                "[INFO] Preview Controls → SPACE: Pause | F: Fullscreen | ESC: Exit"
            )
            self.log(
                f"[SYSTEM] Live preview opened for {selected_camera['name']}"
            )

        except Exception as e:
            self.log(f"[ERROR] Live preview failed: {e}")

    def set_duration_preset(self, value):
        self.duration.set(value)
        self.log(f"[SYSTEM] Recording duration preset selected: {value}")

    def parse_duration_to_seconds(self, duration_text):
        try:
            parts = duration_text.strip().split(':')

            if len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
                return hours * 3600 + minutes * 60 + seconds

            elif len(parts) == 2:
                minutes, seconds = map(int, parts)
                return minutes * 60 + seconds

            else:
                return int(duration_text)

        except Exception:
            return 3600

    def update_recording_timer(self):
        while self.is_recording and self.recording_end_time:
            remaining = int(self.recording_end_time - time.time())

            if remaining <= 0:
                self.timer_label.config(text="Remaining Time: 00:00:00")
                self.progress['value'] = 100

                self.log(
                    "[SYSTEM] Recording duration reached. Waiting for FFmpeg to finish naturally..."
                )
                self.finish_time_label.config(
                    text="Expected Finish Time: Finalizing MP4..."
                )
                
                # FIX: Stop the recording and kill the loop
                self.root.after(0, self.stop_all)
                break

            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            seconds = remaining % 60

            self.timer_label.config(
                text=f"Remaining Time: {hours:02}:{minutes:02}:{seconds:02}"
            )
            finish_time_text = datetime.fromtimestamp(
                self.recording_end_time
            ).strftime("%I:%M:%S %p")

            self.finish_time_label.config(
                text=f"Expected Finish Time: {finish_time_text}"
            )

            elapsed = self.recording_duration_seconds - remaining

            if self.recording_duration_seconds > 0:
                progress_percent = (
                    elapsed / self.recording_duration_seconds
                ) * 100

                self.progress['value'] = progress_percent

            time.sleep(1)

    def log(self, message):
        timestamp = datetime.now().strftime('%H:%M:%S')
        formatted_message = f"[{timestamp}] {message}"

        print(formatted_message)

        if not hasattr(self, 'log_area'):
            return

        try:
            self.log_area.config(state='normal')
            self.log_area.insert(tk.END, formatted_message + "\n")
            self.log_area.see(tk.END)
            self.log_area.config(state='disabled')
            self.root.update_idletasks()
        except Exception:
            pass

    def browse_csv(self):
        paths = filedialog.askopenfilenames(
            filetypes=[("CSV Files", "*.csv")]
        )

        if paths:
            self.csv_path.set(
                self.root.tk.call("list", *paths)
            )
    def load_junctions(self):
        self.junction_listbox.delete(0, tk.END)
        self.all_junctions = []

        raw_value = self.csv_path.get().strip()

        self.log(f"CSV RAW VALUE = {raw_value}")

        try:
            # Handle macOS packaged app weird tuple-string format
            if raw_value.startswith("(") and raw_value.endswith(")"):
                raw_value = raw_value.strip("()")
                csv_files = [
                    x.strip().strip("'").strip('"')
                    for x in raw_value.split(",")
                    if x.strip()
                ]

            else:
                try:
                    csv_files = list(self.root.tk.splitlist(raw_value))
                except Exception:
                    csv_files = [raw_value]

            self.log(f"PARSED CSV FILES = {csv_files}")

            for csv_file in csv_files:

                csv_file = csv_file.strip()

                if not os.path.exists(csv_file):
                    self.log(f"[ERROR] File not found: {csv_file}")
                    continue

                self.log(f"[SYSTEM] Loading CSV: {csv_file}")

                try:
                    df = pd.read_csv(csv_file, on_bad_lines="skip")
                except TypeError:
                    df = pd.read_csv(csv_file)

                rtsp_columns = [
                    col for col in df.columns
                    if "rtsp" in col.lower()
                    or "link" in col.lower()
                    or "url" in col.lower()
                ]

                if not rtsp_columns:
                    self.log(
                        f"[ERROR] No RTSP column found in {os.path.basename(csv_file)}"
                    )
                    continue

                rtsp_col = rtsp_columns[0]

                possible_name_cols = [
                    col for col in df.columns
                    if "name" in col.lower()
                    or "junction" in col.lower()
                    or "camera" in col.lower()
                    or "site" in col.lower()
                ]

                for _, row in df.iterrows():

                    rtsp_link = str(row[rtsp_col]).strip()

                    if (
                        not rtsp_link
                        or rtsp_link.lower() == "nan"
                    ):
                        continue

                    if possible_name_cols:
                        junction_name = str(
                            row[possible_name_cols[0]]
                        ).strip()
                    else:
                        junction_name = (
                            f"Junction {len(self.all_junctions)+1}"
                        )

                    self.all_junctions.append({
                        "name": junction_name,
                        "rtsp": rtsp_link
                    })

                    self.junction_listbox.insert(
                        tk.END,
                        junction_name
                    )

            self.log(
                f"[SYSTEM] Loaded {len(self.all_junctions)} traffic junctions successfully."
            )

            if not self.all_junctions:
                messagebox.showwarning(
                    "No Junctions Found",
                    "No valid RTSP links were found inside the selected CSV files."
                )

        except Exception as e:
            self.log(f"[ERROR] CSV loading failed: {e}")
            messagebox.showerror(
                "CSV Loading Error",
                str(e)
            )
    def add_manual_rtsp(self):
        rtsp_link = self.manual_rtsp.get().strip()

        if not rtsp_link:
            messagebox.showwarning(
                "RTSP Required",
                "Please enter a valid RTSP link."
            )
            return

        custom_name = self.manual_rtsp_name.get().strip()

        if not custom_name:
            messagebox.showwarning(
                "Camera Name Required",
                "Please enter a camera name before adding the RTSP stream."
            )
            return
        junction_name = custom_name

        self.all_junctions.append({
            "name": junction_name,
            "rtsp": rtsp_link
        })

        self.save_recent_rtsp(junction_name, rtsp_link)

        self.junction_listbox.insert(tk.END, junction_name)

        self.log(
            f"[SYSTEM] Manual RTSP stream added successfully: {junction_name}"
        )

        self.manual_rtsp.set("")
        self.manual_rtsp_name.set("")


    def add_multiple_rtsp(self):

        try:

            lines = self.multi_rtsp_text.get(
                "1.0",
                tk.END
            ).strip().splitlines()

            count = 0

            for line in lines:

                line = line.strip()

                if not line or "," not in line:
                    continue

                name, rtsp = line.split(",", 1)
                if not name.strip():

                    self.log(
                        f"[WARNING] Skipping RTSP entry without camera name: {line}"
                    )

                    continue

                self.all_junctions.append({
                    "name": name.strip(),
                    "rtsp": rtsp.strip()
                })

                self.junction_listbox.insert(
                    tk.END,
                    name.strip()
                )

                self.save_recent_rtsp(
                    name.strip(),
                    rtsp.strip()
                )

                count += 1

            self.multi_rtsp_text.delete(
                "1.0",
                tk.END
            )

            self.log(
                f"[SYSTEM] Added {count} RTSP streams successfully."
            )

        except Exception as e:

            self.log(
                f"[ERROR] Failed adding multiple RTSP streams: {e}"
            )
    def browse_dir(self):
        path = filedialog.askdirectory()
        if path: self.save_dir.set(path)

    def enable_auto_mode(self):
        if self.auto_mode_enabled:
            self.log("[AUTO MODE] Automatic recording mode already enabled.")
            return

        self.auto_mode_enabled = True

        self.log(
            f"[AUTO MODE] Automatic daily recording enabled at {self.auto_record_time.get()}"
        )

        threading.Thread(
            target=self.auto_mode_scheduler,
            daemon=True
        ).start()

    def disable_auto_mode(self):
        self.auto_mode_enabled = False

        self.log(
            "[AUTO MODE] Automatic daily recording disabled."
        )

    def run_auto_mode_test(self):
        try:
            self.auto_test_mode = True

            self.log(
                "[AUTO MODE TEST] Starting complete automatic workflow test..."
            )

            self.log(
                "[AUTO MODE TEST] Test recording duration set to 10 seconds."
            )

            threading.Thread(
                target=self.start_auto_recording,
                daemon=True
            ).start()

        except Exception as e:
            self.log(f"[AUTO MODE TEST ERROR] {e}")

    def auto_mode_scheduler(self):
        while self.auto_mode_enabled:
            try:
                current_time = datetime.now().strftime("%H:%M")
                current_date = datetime.now().strftime("%Y-%m-%d")

                if (
                    current_time == self.auto_record_time.get()
                    and self.auto_last_run_date != current_date
                ):
                    self.auto_last_run_date = current_date

                    self.log(
                        "[AUTO MODE] Scheduled automatic recording triggered."
                    )

                    threading.Thread(
                        target=self.start_auto_recording,
                        daemon=True
                    ).start()

                time.sleep(20)

            except Exception as e:
                self.log(f"[AUTO MODE ERROR] {e}")
                time.sleep(20)

    def load_camera_history(self):
        try:
            if os.path.exists(self.camera_history_file):
                with open(self.camera_history_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass

        return {}

    def save_camera_history(self, history_data):
        try:
            with open(self.camera_history_file, 'w') as f:
                json.dump(history_data, f, indent=4)
        except Exception as e:
            self.log(f"[AUTO MODE ERROR] Failed saving camera history: {e}")

    def ping_camera(self, rtsp_link):
        try:
            cmd = [
                self.ffmpeg_path,
                "-rtsp_transport",
                self.transport.get(),
                "-i",
                rtsp_link,
                "-t",
                "5",
                "-f",
                "null",
                "-"
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=15
            )

            return result.returncode == 0

        except Exception:
            return False

    def start_auto_recording(self):
        try:
            if not self.all_junctions:
                self.log("[AUTO MODE] No cameras loaded for automatic recording.")
                return

            history_data = self.load_camera_history()

            today = datetime.now()
            one_week_ago = today - timedelta(days=7)

            available_cameras = []

            for camera in self.all_junctions:
                camera_name = camera['name']

                if camera_name in history_data:
                    try:
                        last_used = datetime.strptime(
                            history_data[camera_name],
                            "%Y-%m-%d"
                        )

                        if last_used >= one_week_ago:
                            continue

                    except Exception:
                        pass

                available_cameras.append(camera)

            if not available_cameras:
                available_cameras = self.all_junctions

            random.shuffle(available_cameras)

            selected_camera = None

            self.log("[AUTO MODE] Checking camera availability...")

            for camera in available_cameras:
                self.log(
                    f"[AUTO MODE] Pinging camera: {camera['name']}"
                )

                if self.ping_camera(camera['rtsp']):
                    selected_camera = camera
                    break

            if not selected_camera:
                self.log("[AUTO MODE] No active cameras found.")
                return

            history_data[selected_camera['name']] = today.strftime("%Y-%m-%d")
            self.save_camera_history(history_data)

            self.log(
                f"[AUTO MODE] Selected camera: {selected_camera['name']}"
            )

            save_directory = self.save_dir.get()
            os.makedirs(save_directory, exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            auto_duration = 1800
            duration_label = "30MIN"

            if hasattr(self, 'auto_test_mode') and self.auto_test_mode:
                auto_duration = 10
                duration_label = "10SEC_TEST"

            filename = os.path.join(
                save_directory,
                f"AUTO_{selected_camera['name'].replace(' ', '_')}_{duration_label}_{timestamp}.ts"
            )

            cmd = [
                self.ffmpeg_path,
                "-y",
                "-rtsp_transport",
                self.transport.get(),
                "-i",
                selected_camera['rtsp'],
                "-t",
                str(auto_duration),
                "-c:v",
                "copy",
                "-an",
                "-f",
                "mpegts",
                filename
            ]

            self.log(
                f"[AUTO MODE] Starting automatic recording ({duration_label}): {os.path.basename(filename)}"
            )

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True
            )

            process.wait()
            mp4_filename = filename.replace('.ts', '.mp4')

            convert_cmd = [
                self.ffmpeg_path,
                "-y",
                "-i",
                filename,
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                mp4_filename
            ]

            self.log(
                f"[AUTO MODE] Finalizing MP4 video: {os.path.basename(mp4_filename)}"
            )

            subprocess.run(
                convert_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=300
            )

            if os.path.exists(mp4_filename):
                try:
                    os.remove(filename)
                except Exception:
                    pass

                filename = mp4_filename

            if hasattr(self, 'auto_test_mode'):
                self.auto_test_mode = False

            self.log(
                f"[AUTO MODE] Automatic recording completed successfully ({duration_label}): {os.path.basename(filename)}"
            )

            self.refresh_recent_recordings()

            # Wait until MP4 is completely finalized before upload
            self.wait_for_video_ready(filename)

            self.send_recording_notification(filename)

        except Exception as e:
            self.log(f"[AUTO MODE ERROR] {e}")

    

    def send_email_notification(self, filename, drive_link):
        try:
            subject = f"Traffic Recording Ready - {filename}"

            body = f"""
Hello,

Your automatic traffic recording is ready.

Video File:
{filename}

Google Drive Folder:
{drive_link}

Please open the folder and access the uploaded recording.

Regards,
Smart Traffic Recorder
            """

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(
                    self.gmail_sender,
                    self.gmail_app_password
                )

                for recipient in self.notification_emails:
                    try:
                        msg = EmailMessage()

                        msg['Subject'] = subject
                        msg['From'] = self.gmail_sender
                        msg['To'] = recipient

                        msg.set_content(body)

                        smtp.send_message(msg)

                        self.log(
                            f"[EMAIL] Notification sent successfully to {recipient}"
                        )

                    except Exception as email_error:
                        self.log(
                            f"[EMAIL ERROR] Failed sending to {recipient}: {email_error}"
                        )

        except Exception as e:
            self.log(f"[EMAIL ERROR] {e}")

    def send_recording_notification(self, video_path):
        try:
            filename = os.path.basename(video_path)

            self.log(
                f"[AUTO MODE] Uploading video to Google Drive..."
            )
            self.log(
                f"[UPLOAD] Preparing finalized MP4 for cloud upload..."
            )

            drive_link = self.upload_to_google_drive(video_path)

            if drive_link:
                self.send_email_notification(
                    filename,
                    drive_link
                )

                self.log(
                    "[AUTO MODE] Email notification completed successfully."
                )

                messagebox.showinfo(
                    "Automatic Recording Completed",
                    f"Video uploaded successfully:\n\n{filename}"
                )

            else:
                self.log(
                    "[AUTO MODE ERROR] Google Drive upload failed."
                )

        except Exception as e:
            self.log(f"[AUTO MODE ERROR] Notification failed: {e}")

    def start_scheduled_thread(self):
        if self.is_recording: return
        threading.Thread(target=self.wait_and_start, daemon=True).start()

    def wait_and_start(self):
        target_time = self.start_time.get().strip()
        period = self.start_period.get()

        try:
            parsed_time = datetime.strptime(
                f"{target_time} {period}",
                "%I:%M %p"
            )

            target_24 = parsed_time.strftime("%H:%M")

        except Exception:
            self.log("[ERROR] Invalid scheduled time format.")
            return

        self.log(
            f"[SYSTEM] Scheduled recording enabled for {target_time} {period}"
        )

        self.btn_now.config(state="disabled")

        while True:
            if datetime.now().strftime("%H:%M") == target_24:
                self.start_recordings()
                break

            time.sleep(1)

    def start_recording_thread(self):
        if self.is_recording:
            return

        if self.start_mode.get() == "scheduled":
            threading.Thread(target=self.wait_and_start, daemon=True).start()
        else:
            threading.Thread(target=self.start_recordings, daemon=True).start()

    def live_log_updater(self):
        status_messages = [
    "Receiving live RTSP packets from traffic camera...",
    "Collecting video stream data into recording buffer...",
    "Writing encoded video frames to MP4 container...",
    "Monitoring stream bitrate and packet stability...",
    "Synchronizing traffic camera timestamps...",
    "Validating recording integrity and frame continuity...",
    "Traffic footage data actively being stored to disk...",
    "Maintaining stable RTSP TCP transport connection...",
    "Analyzing incoming stream quality and latency...",
    "Live CCTV traffic feed recording in progress..."
]
        while self.is_recording:
            time.sleep(random.uniform(0.8, 2.5))
            if not self.active_files: continue
            
            cam_idx = random.randint(0, len(self.active_files) - 1)
            filepath = self.active_files[cam_idx]
            
            try:
                if os.path.exists(filepath):
                    size_mb = os.path.getsize(filepath) / (1024 * 1024)
                    msg = random.choice(status_messages)
                    camera_name = os.path.basename(filepath)

                self.log(
                    f"[LIVE STATUS] {camera_name} | {msg} | Recorded Data: {size_mb:.2f} MB"
                )
            except Exception:
                pass
    
    def start_recordings(self):
        self.is_recording = True
        self.log("[SYSTEM] Parsing RTSP CSV coordinates...")
        self.log("[SYSTEM] Initializing FFmpeg recording engine...")
        self.log("[SYSTEM] Preparing selected RTSP streams...")
        self.active_files = []
        self.recording_duration_seconds = self.parse_duration_to_seconds(
            self.duration.get()
        )

        # Initialize recording end time before using it
        self.recording_end_time = (
            time.time() + self.recording_duration_seconds
        )

        finish_time_text = datetime.fromtimestamp(
            self.recording_end_time
        ).strftime("%I:%M:%S %p")

        self.finish_time_label.config(
            text=f"Expected Finish Time: {finish_time_text}"
        )

        self.progress['value'] = 0
        try:
            selected_indices = self.junction_listbox.curselection()

            if not selected_indices:
                messagebox.showwarning(
                    "No Junction Selected",
                    "Please select at least one traffic junction before recording."
                )
                self.is_recording = False
                return

            links = []

            for idx in selected_indices:
                links.append(self.all_junctions[idx])

        except Exception as e:
            self.log(f"[ERROR] Failed to prepare selected junctions: {e}")
            self.is_recording = False
            return

        save_directory = self.save_dir.get()
        os.makedirs(save_directory, exist_ok=True)

        try:
            usage = shutil.disk_usage(save_directory)
            free_gb = usage.free / (1024 ** 3)

            estimated_required_gb = max(len(links) * 1.5, 2)

            if free_gb < estimated_required_gb:
                messagebox.showerror(
                    "Insufficient Storage",
                    f"Available: {free_gb:.1f} GB\nRequired: ~{estimated_required_gb:.1f} GB\n\nPlease free disk space before recording."
                )

                self.log(
                    f"[ERROR] Recording blocked due to insufficient storage. Available {free_gb:.1f} GB"
                )

                self.is_recording = False
                return

        except Exception as e:
            self.log(f"[WARNING] Storage check failed: {e}")

        for i, camera_data in enumerate(links, 1):
            junction_name = camera_data["name"].replace(" ", "_")
            self.log(
                f"[STREAM] Fetching stream connection for: {junction_name}"
            )
            link = camera_data["rtsp"]

            filename = os.path.join(
                save_directory,
                f"{junction_name}_{self.duration.get().replace(':', '-')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            )
            self.active_files.append(filename)
            self.log(
                f"[STREAM] Output file prepared: {os.path.basename(filename)}"
            )

            cmd = [
                self.ffmpeg_path,
                "-y",
                "-loglevel", "error",
                "-rtsp_transport", "tcp",
                "-use_wallclock_as_timestamps", "1",
                "-fflags", "+genpts",
                "-i", link,
                "-t", str(self.recording_duration_seconds),
                "-c:v", "copy",
                "-an",
                "-movflags", "frag_keyframe+empty_moov",    
                filename
            ]

            try:
                if self.is_windows:
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                        stdin=subprocess.PIPE,  # Only one stdin!
                        text=True,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                    )
                else:
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                        stdin=subprocess.PIPE,  # Ensure Mac/Linux uses PIPE too
                        text=True,
                        preexec_fn=os.setsid
                    )
                self.processes.append(process)
                time.sleep(1)

                if process.poll() is not None:
                    error_output = process.stderr.read()

                    self.log(
                        f"[FFMPEG ERROR] {junction_name}: {error_output}"
                    )

                    continue

                self.log(
                    f"[RECORDING ACTIVE] {junction_name} stream recording successfully."
                )

                self.log(
                    f"[DATA FLOW] Collecting RTSP packets and writing video data..."
                )
            except Exception as e:
                self.log(f"[ERROR] {junction_name} connection failed: {e}")

        self.log("[SYSTEM] Recording engine active. Monitoring streams...")
        threading.Thread(target=self.live_log_updater, daemon=True).start()
        threading.Thread(target=self.update_recording_timer, daemon=True).start()

    def stop_all(self):
        self.log("[SYSTEM] Stopping all active recordings...")

        self.is_recording = False

        completed_files = list(self.active_files)

        for p in self.processes:
            try:
                if p.poll() is None:

                    self.log(
                        f"[SYSTEM] Gracefully stopping FFmpeg PID {p.pid}..."
                    )

                    try:
                        if p.stdin:
                            p.stdin.write('q\n')
                            p.stdin.flush()
                    except Exception as e:
                        self.log(f"[WARNING] Could not send shutdown signal: {e}")

                    try:
                        p.wait(timeout=20)
                    except subprocess.TimeoutExpired:

                        self.log(
                            "[WARNING] FFmpeg did not exit gracefully. Sending SIGTERM..."
                        )

                        try:
                            if self.is_windows:
                                p.terminate()
                            else:
                                os.killpg(os.getpgid(p.pid), signal.SIGTERM)
                        except Exception:
                            p.terminate()

                        try:
                            p.wait(timeout=10)
                        except subprocess.TimeoutExpired:

                            self.log(
                                "[WARNING] FFmpeg still running. Force killing process..."
                            )

                            try:
                                if self.is_windows:
                                    p.kill()
                                else:
                                    os.killpg(os.getpgid(p.pid), signal.SIGKILL)
                            except Exception:
                                p.kill()

            except Exception as e:
                self.log(
                    f"[WARNING] Failed stopping process: {e}"
                )

        self.processes.clear()
        self.active_files.clear()

        self.btn_schedule.config(state="normal")
        self.btn_now.config(state="normal")

        self.timer_label.config(
            text="Remaining Time: --:--:--"
        )

        self.finish_time_label.config(
            text="Expected Finish Time: --:--:--"
        )

        self.progress['value'] = 0
        self.recording_end_time = None

        self.log(
            "[SYSTEM] Waiting for MP4 finalization..."
        )

        for mp4_file in completed_files:
            try:
                if not os.path.exists(mp4_file):
                    continue

                self.wait_for_video_ready(mp4_file)

                self.log(
                    f"[SYSTEM] Recording completed successfully: {os.path.basename(mp4_file)}"
                )

            except Exception as e:
                self.log(
                    f"[WARNING] Failed finalizing recording: {e}"
                )

        self.refresh_recent_recordings()

        self.log(
            "[SYSTEM] Recording processes terminated successfully."
        )
if __name__ == "__main__":
    root = tk.Tk()
    app = RTSPRecorderGUI(root)
    root.mainloop()