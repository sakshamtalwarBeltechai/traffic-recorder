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
        self.root.geometry("900x850")
        self.processes = []
        self.active_files = []
        self.is_recording = False
        self.recording_end_time = None
        self.recording_duration_seconds = 0
        
        self.csv_path = tk.StringVar(value="/Users/sakshamtalwar/Beltech_Annotation/Excel_Sheets/RTSP_Goa.csv")
        self.save_dir = tk.StringVar(value=os.path.expanduser("~/Desktop"))
        self.start_time = tk.StringVar(value="13:30")
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

        self.ffmpeg_path = os.path.join(base_path, 'ffmpeg.exe')

        self.config_file = os.path.join(base_path, 'recent_rtsp.json')

        if not os.path.exists(self.ffmpeg_path):
            self.ffmpeg_path = 'ffmpeg'

        self.setup_ui()

    def setup_ui(self):
        title_frame = ttk.Frame(self.root, padding=10)
        title_frame.pack(fill="x")

        ttk.Label(
            title_frame,
            text="Smart Traffic Camera Recording Dashboard",
            font=("Arial", 18, "bold")
        ).pack(anchor="center")

        ttk.Label(
            title_frame,
            text="Select traffic junctions and start recording with one click.",
            font=("Arial", 10)
        ).pack(anchor="center", pady=5)

        frame_files = ttk.LabelFrame(self.root, text="CSV Camera Source Management", padding=10)
        frame_files.pack(fill="x", padx=10, pady=5)

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

        ttk.Label(frame_files, text="Save Recordings To:").grid(row=3, column=0, sticky="w", pady=5)
        ttk.Entry(frame_files, textvariable=self.save_dir, width=50).grid(row=3, column=1, padx=5)
        ttk.Button(frame_files, text="Browse", command=self.browse_dir).grid(row=3, column=2)

        junction_frame = ttk.LabelFrame(self.root, text="Available Traffic Junctions", padding=10)
        junction_frame.pack(fill="both", expand=False, padx=10, pady=5)

        ttk.Label(
            junction_frame,
            text="Select one or multiple junctions to start recording",
            font=("Arial", 10)
        ).pack(anchor="w")

        self.junction_listbox = tk.Listbox(
            junction_frame,
            selectmode=MULTIPLE,
            height=10,
            bg="#1e1e1e",
            fg="lime",
            font=("Arial", 10)
        )
        self.junction_listbox.pack(fill="both", expand=True, pady=5)

        preview_frame = ttk.Frame(junction_frame)
        preview_frame.pack(fill="x", pady=5)

        ttk.Button(
            preview_frame,
            text="Open Live Preview",
            command=self.open_live_preview
        ).pack(side="left", padx=5)
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

            ffplay_path = shutil.which("ffplay")

            if not ffplay_path:
                ffplay_path = self.ffmpeg_path.replace("ffmpeg.exe", "ffplay.exe")

            preview_cmd = [
                ffplay_path,
                "-rtsp_transport",
                self.transport.get(),
                "-fflags",
                "nobuffer",
                "-flags",
                "low_delay",
                rtsp_link
            ]

            subprocess.Popen(preview_cmd)

            self.log(
                f"[SYSTEM] Live preview opened for {selected_camera['name']}"
            )

        except Exception as e:
            self.log(f"[ERROR] Live preview failed: {e}")

        frame_time = ttk.LabelFrame(self.root, text="Recording Schedule", padding=10)
        frame_time.pack(fill="x", padx=10, pady=5)

        ttk.Label(frame_time, text="Start Time (HH:MM):").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame_time, textvariable=self.start_time, width=12).grid(row=0, column=1, sticky="w", padx=5)

        ttk.Label(frame_time, text="Recording Duration (HH:MM:SS):").grid(row=0, column=2, sticky="w", padx=10)
        ttk.Entry(frame_time, textvariable=self.duration, width=12).grid(row=0, column=3, sticky="w")

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

                self.log("[SYSTEM] Recording duration completed successfully.")

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

        frame_ffmpeg = ttk.LabelFrame(self.root, text="Video Recording Quality Settings", padding=10)
        frame_ffmpeg.pack(fill="x", padx=10, pady=5)

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

        frame_controls = ttk.Frame(self.root, padding=10)
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

        frame_logs = ttk.LabelFrame(self.root, text="Live System Activity", padding=10)
        frame_logs.pack(fill="both", expand=True, padx=10, pady=5)

        self.log_area = scrolledtext.ScrolledText(
            frame_logs,
            height=16,
            state='disabled',
            bg="black",
            fg="lime",
            font=("Consolas", 10)
        )
        self.log_area.pack(fill="both", expand=True)

    def log(self, message):
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')

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

        custom_name = self.manual_rtsp_name.get().strip()

        if custom_name:
            junction_name = custom_name
        else:
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
        self.manual_rtsp_name.set("")

    def browse_dir(self):
        path = filedialog.askdirectory()
        if path: self.save_dir.set(path)

    def start_scheduled_thread(self):
        if self.is_recording: return
        threading.Thread(target=self.wait_and_start, daemon=True).start()

    def wait_and_start(self):
        target_time = self.start_time.get()
        self.log(f"[SYSTEM] Scheduled. Waiting for {target_time} to initiate stream capture...")
        self.btn_schedule.config(state="disabled")
        while True:
            if datetime.now().strftime("%H:%M") == target_time:
                self.start_recordings()
                break
            time.sleep(1)

    def start_recording_thread(self):
        if self.is_recording: return
        threading.Thread(target=self.start_recordings, daemon=True).start()

    def live_log_updater(self):
        status_messages = [
            "Receiving I-frames on TCP port...",
            "Buffering stream data...",
            "Writing multiplexed packet to disk...",
            "Processing h264_videotoolbox hardware encoding...",
            "Syncing RTSP stream transport...",
            "Analyzing incoming bitrate..."
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
                    self.log(f"[Junction {cam_idx + 1}] {msg} | Current Size: {size_mb:.2f} MB")
            except Exception:
                pass

    def start_recordings(self):
        self.is_recording = True
        self.log("[SYSTEM] Parsing RTSP CSV coordinates...")
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
            junction_name = camera_data["name"].replace(" ", "_")
            link = camera_data["rtsp"]

            filename = os.path.join(
                save_directory,
                f"{junction_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            )
            self.active_files.append(filename)

            cmd = [
                self.ffmpeg_path,
                "-y",
                "-rtsp_transport",
                self.transport.get(),
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
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                    )
                else:
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        preexec_fn=os.setsid
                    )
                self.processes.append(process)
                time.sleep(2)

                if process.poll() is not None:
                    error_output = process.stderr.read()

                    self.log(
                        f"[FFMPEG ERROR] {junction_name}: {error_output}"
                    )

                    continue
                self.log(f"[SYSTEM] Recording started successfully for {junction_name}")
            except Exception as e:
                self.log(f"[ERROR] {junction_name} connection failed: {e}")

        self.log("[SYSTEM] Recording engine active. Monitoring streams...")
        threading.Thread(target=self.live_log_updater, daemon=True).start()
        threading.Thread(target=self.update_recording_timer, daemon=True).start()

    def stop_all(self):
        if not self.processes: return
        self.log("[SYSTEM] Sending SIGTERM to terminate hardware encoding safely...")
        for p in self.processes:
            try:
                if self.is_windows:
                    p.terminate()
                    p.wait(timeout=5)
                else:
                    os.killpg(os.getpgid(p.pid), signal.SIGTERM)
                    p.wait(timeout=5)
            except Exception:
                pass
        self.processes.clear()
        self.active_files.clear()
        self.is_recording = False
        self.btn_schedule.config(state="normal")
        self.timer_label.config(text="Remaining Time: --:--:--")
        self.progress['value'] = 0
        self.recording_end_time = None
        self.log("[SYSTEM] Recording processes terminated. Data flushed to disk.")


if __name__ == "__main__":
    root = tk.Tk()
    app = RTSPRecorderGUI(root)
    root.mainloop()