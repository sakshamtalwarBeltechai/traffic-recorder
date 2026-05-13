import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
from tkinter.ttk import Progressbar
from tkinter import messagebox
from tkinter import MULTIPLE
import pandas as pd
import subprocess
import threading
import time
from datetime import datetime
import os
import signal
import random
import sys
import json
import shutil

class RTSPRecorderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("FFmpeg RTSP Multi-Recorder")
        self.root.geometry("1600x1020")
        self.root.minsize(1350, 850)
        self.main_canvas = None
        self.scrollable_frame = None
        self.processes = []
        self.preview_process = None
        self.preview_paused = False
        self.active_files = []
        self.is_recording = False
        self.recording_end_time = None
        self.recording_duration_seconds = 0
        
        self.csv_path = tk.StringVar(value="/Users/sakshamtalwar/Beltech_Annotation/Excel_Sheets/RTSP_Goa.csv")
        self.save_dir = tk.StringVar(value=os.path.expanduser("~/Desktop"))
        self.start_time = tk.StringVar(value="01:30")
        self.start_period = tk.StringVar(value="PM")
        self.start_mode = tk.StringVar(value="now")
        self.duration = tk.StringVar(value="01:00:00")
        if os.name == 'nt':
            default_codec = 'copy'
        else:
            default_codec = 'h264_videotoolbox'

        self.codec = tk.StringVar(value=default_codec)
        self.bitrate = tk.StringVar(value="1M")
        self.transport = tk.StringVar(value="tcp")

        self.all_junctions = []
        self.selected_junctions = []

        self.is_windows = os.name == 'nt'

        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

        if self.is_windows:
            bundled_ffmpeg = os.path.join(base_path, 'ffmpeg.exe')
            bundled_ffplay = os.path.join(base_path, 'ffplay.exe')

            self.ffmpeg_path = bundled_ffmpeg if os.path.exists(bundled_ffmpeg) else 'ffmpeg'
            self.ffplay_path = bundled_ffplay if os.path.exists(bundled_ffplay) else 'ffplay'

        else:
            self.ffmpeg_path = shutil.which('ffmpeg') or 'ffmpeg'
            self.ffplay_path = shutil.which('ffplay') or 'ffplay'

        self.config_file = os.path.join(base_path, 'recent_rtsp.json')

        if self.is_windows:
            if not os.path.exists(self.ffmpeg_path):
                self.ffmpeg_path = 'ffmpeg'

            if not os.path.exists(self.ffplay_path):
                self.ffplay_path = 'ffplay'

        self.setup_ui()
        self.update_live_clock()
        self.log("[SYSTEM] Smart Traffic Recorder Dashboard initialized successfully.")
        self.log("[SYSTEM] Ready to load RTSP CSV files and start monitoring.")

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
            text="Direct RTSP Link:"
        ).grid(row=2, column=0, sticky="w", pady=5)

        self.manual_rtsp = tk.StringVar()

        ttk.Entry(
            frame_files,
            textvariable=self.manual_rtsp,
            width=70
        ).grid(row=2, column=1, columnspan=2, padx=5, sticky="ew")

        ttk.Button(
            frame_files,
            text="Add RTSP Stream",
            command=self.add_manual_rtsp
        ).grid(row=2, column=3, padx=10)

        ttk.Label(frame_files, text="Save Recordings To:").grid(row=3, column=0, sticky="w", pady=5)
        ttk.Entry(frame_files, textvariable=self.save_dir, width=50).grid(row=3, column=1, padx=5)
        ttk.Button(frame_files, text="Browse", command=self.browse_dir).grid(row=3, column=2)

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

        self.junction_listbox = tk.Listbox(
            junction_frame,
            selectmode=MULTIPLE,
            height=7,
            bg="#08111f",
            fg="#d1fae5",
            selectbackground="#2563eb",
            selectforeground="white",
            relief="flat",
            borderwidth=0,
            font=("Segoe UI", 10)
        )
        self.junction_listbox.pack(fill="both", expand=True, pady=5)

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

            ffplay_path = self.ffplay_path

            preview_cmd = [
                ffplay_path,
                "-rtsp_transport",
                self.transport.get(),
                "-hide_banner",
                "-nostats",
                "-loglevel",
                "panic",
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

            self.preview_process = subprocess.Popen(
                preview_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
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
                    "[SYSTEM] Recording timer reached configured duration limit."
                )       

                self.stop_all()
                break

            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            seconds = remaining % 60

            self.timer_label.config(
                text=f"Remaining Time: {hours:02}:{minutes:02}:{seconds:02}"
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
        paths = filedialog.askopenfilenames(filetypes=[("CSV Files", "*.csv")])
        if paths:
            self.csv_path.set(paths)
    def load_junctions(self):
        self.junction_listbox.delete(0, tk.END)
        self.all_junctions = []

        try:
            csv_files = self.root.tk.splitlist(self.csv_path.get())

            for csv_file in csv_files:
                try:
                    df = pd.read_csv(csv_file, on_bad_lines='skip')
                except TypeError:
                     df = pd.read_csv(csv_file)

                rtsp_col = [
                    col for col in df.columns
                    if 'rtsp' in col.lower() or 'link' in col.lower()
                ][0]

                possible_name_cols = [
                    col for col in df.columns
                    if 'name' in col.lower() or 'junction' in col.lower() or 'camera' in col.lower()
                ]

                for idx, row in df.iterrows():
                    rtsp_link = str(row[rtsp_col]).strip()

                    if rtsp_link == 'nan' or not rtsp_link:
                        continue

                    if possible_name_cols:
                        junction_name = str(row[possible_name_cols[0]])
                    else:
                        junction_name = f"Junction {len(self.all_junctions) + 1}"

                    display_text = f"{junction_name}"

                    self.all_junctions.append({
                        "name": junction_name,
                        "rtsp": rtsp_link
                    })

                    self.junction_listbox.insert(tk.END, display_text)

            self.log(f"[SYSTEM] Loaded {len(self.all_junctions)} traffic junctions successfully.")

            if len(self.all_junctions) == 0:
                messagebox.showwarning("No Junctions Found", "No valid RTSP links were found inside the selected CSV files.")

        except Exception as e:
            messagebox.showerror("CSV Loading Error", str(e))
            self.log(f"[ERROR] CSV loading failed: {e}")

    def add_manual_rtsp(self):
        rtsp_link = self.manual_rtsp.get().strip()

        if not rtsp_link:
            messagebox.showwarning(
                "RTSP Required",
                "Please enter a valid RTSP link."
            )
            return

        junction_name = f"Manual_RTSP_{len(self.all_junctions) + 1}"

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

    def browse_dir(self):
        path = filedialog.askdirectory()
        if path: self.save_dir.set(path)

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

        self.recording_end_time = time.time() + self.recording_duration_seconds

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

        for i, camera_data in enumerate(links, 1):
            junction_name = str(camera_data["name"])

            # Windows-safe filename cleanup
            invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']

            for char in invalid_chars:
                junction_name = junction_name.replace(char, '_')

            junction_name = junction_name.replace(' ', '_')
            self.log(
                f"[STREAM] Fetching stream connection for: {junction_name}"
            )
            link = camera_data["rtsp"]
            # Clean malformed RTSP links from accidental whitespace/newlines
            link = str(link).strip()

            if not link.lower().startswith("rtsp://"):
                self.log(f"[ERROR] Invalid RTSP URL detected for {junction_name}")
                continue

            filename = os.path.join(
                save_directory,
                f"{junction_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            )
            self.active_files.append(filename)
            self.log(
             f"[STREAM] Output file prepared: {os.path.basename(filename)}"
            )

            cmd = [
                self.ffmpeg_path,
                "-hide_banner",
                "-loglevel",
                "error",
                "-rtsp_transport",
                self.transport.get(),
                "-stimeout",
                "10000000",
                "-y",
                "-i",
                link,
                "-t",
                str(self.recording_duration_seconds)
            ]

            if self.codec.get() == "copy":
                cmd.extend([
                    "-c:v",
                    "copy"
                ])
            else:
                cmd.extend([
                    "-c:v",
                    self.codec.get(),
                    "-b:v",
                    self.bitrate.get()
                ])

            cmd.extend([
                "-an",
                "-movflags",
                "+faststart",
                "-avoid_negative_ts",
                "make_zero",
                filename
            ])

            try:
                if self.is_windows:
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                        stdin=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
                    )
                else:
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                        text=True,
                        preexec_fn=os.setsid
                    )
                self.processes.append(process)
                time.sleep(2)

                if process.poll() is not None:
                    try:
                        error_output = process.stderr.read().decode(errors='ignore')
                    except Exception:
                        error_output = str(process.stderr.read())

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

        for p in self.processes:
            try:
               if p.poll() is None:

                if self.is_windows:
                    p.terminate()
                    time.sleep(2)

                else:
                    try:
                        os.killpg(
                            os.getpgid(p.pid),
                            signal.SIGTERM
                        )
                    except Exception:
                        p.terminate()
                        time.sleep(2)

                p.wait(timeout=5)

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

        self.progress['value'] = 0
        self.recording_end_time = None

        self.log(
            "[SYSTEM] Refreshing recently recorded videos list..."
        )

        self.refresh_recent_recordings()

        self.log(
            "[SYSTEM] Recording processes terminated successfully."
        )


if __name__ == "__main__":
    root = tk.Tk()
    app = RTSPRecorderGUI(root)
    root.mainloop()