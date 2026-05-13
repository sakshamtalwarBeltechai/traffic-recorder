# Smart Traffic Camera Recording Dashboard

A professional desktop dashboard for recording multiple RTSP traffic camera streams using FFmpeg.

Built using Python and designed for traffic monitoring operators, CCTV control rooms, and surveillance teams.

---

# Features

- Multi-camera RTSP recording
- Load one or multiple CSV camera lists
- Select specific junctions for recording
- Real-time activity logs
- Scheduled recording support
- FFmpeg-based recording engine
- Dashboard-style desktop interface
- Windows executable build support
- Multi-stream recording
- Operator-friendly interface
- Dark theme UI

---

# Technologies Used

- Python
- PySide6
- FFmpeg
- Pandas
- PyInstaller
- GitHub Actions

---

# Project Structure

text Traffic_Recorder/ │ ├── record_goa.py ├── requirements.txt ├── run.bat │ ├── .github/ │   └── workflows/ │       └── build.yml 

---

# CSV Format

The application automatically detects RTSP and camera/junction columns.

Example CSV:

| Junction Name | RTSP Link |
|---|---|
| MG Road | rtsp://username:password@ip |
| Silk Board | rtsp://username:password@ip |

Supported column keywords:

## RTSP Columns
- rtsp
- link

## Junction Name Columns
- name
- junction
- camera

---

# Installation (Development)

## Install Python Packages

bash pip install -r requirements.txt 

---

# Run Application

bash python record_goa.py 

---

# Build Windows EXE

## Local Build

bash pyinstaller --onefile --windowed record_goa.py 

---

# GitHub Actions Auto Build

The repository includes a GitHub Actions workflow that automatically builds a Windows executable on every push to the main branch.

Workflow file:

text .github/workflows/build.yml 

Generated executable can be downloaded from:

GitHub → Actions → Successful Workflow → Artifacts

---

# FFmpeg Requirement

The application requires FFmpeg for recording RTSP streams.

Recommended setup:

text project/ │ ├── record_goa.py ├── ffmpeg.exe 

Future versions will bundle FFmpeg automatically into the executable.

---

# Current Limitations

- Live preview thumbnails not implemented yet
- FFmpeg logs are currently hidden
- Windows process handling improvements pending
- FFmpeg bundling still in progress

---

# Planned Features

- Live camera preview
- Online/offline indicators
- Storage monitoring
- Camera cards dashboard
- Recording history
- Search and filtering
- Auto reconnect
- Event-based recording
- AI traffic analytics
- Number plate detection
- Traffic violation recording

---

# Recommended Use Cases

- Traffic monitoring centers
- CCTV operations
- RTSP stream management
- Junction surveillance
- Multi-camera recording systems

---

# Author

Developed by Saksham Talwar / Beltech AI

---

# License

This project is intended for internal and operational use.
