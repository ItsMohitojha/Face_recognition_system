# Project Context: Face Recognition Attendance System

A concise technical guide, architecture reference, and setup manual for the Face Recognition Attendance System.

---

## 📖 1. Project Overview
This project is an automated attendance system using real-time facial recognition. It reads images of registered students, computes their facial features, and runs a live webcam capture to match faces and log attendance into a CSV file.

### Core Tech Stack
* **Python 3.8+**
* **Streamlit & streamlit-webrtc**: For the interactive web interface.
* **OpenCV**: For local video frame processing and window GUI.
* **dlib / face_recognition**: For face detection (finding faces) and face encoding (128-dimensional vector representation).
* **filelock**: Ensures thread-safe reading/writing to the attendance CSV sheet.

---

## 🛠️ 2. File Directory & Architecture
The project structure consists of the following components:

```
├── .gitignore               # Excludes virtual environments, local caches, and private dataset folders (images/, encodings/)
├── README.md                # Project landing page and setup guide
├── project_context.md       # [This File] Architecture and context reference
├── config.py                # Centralized file paths and datetime format configurations
├── students.csv             # Master roster mapping Enrollment ID to Name and Image Filename
├── Attendance.csv           # DB sheet logging dates as columns, students as rows, and present times
├── app.py                   # Main Streamlit web application with WebRTC streaming
├── attendance.py            # Logic for reading/writing Attendance.csv and syncing students
├── encode.py                # Standalone script to generate face encodings (.npy) from images/
├── decode.py                # Standalone local webcam checker utilizing OpenCV
├── mark_absent.py           # Utility to mark all unmarked student cells as "Absent"
├── test_attendance.py       # Unit tests verifying file updates, locks, and synchronization
└── requirements.txt         # Project dependencies (opencv, numpy, face_recognition, filelock)
```

---

## 🔄 3. Key System Workflows

### 3.1 Encoding Faces (`encode.py`)
1. Reads student rows from `students.csv`.
2. Locates student photos in `images/` directory.
3. Loads the image using OpenCV, converts color channel layout (`BGR` ➔ `RGB`).
4. Generates a 128-dimensional face embedding using `face_recognition`.
5. Serializes lists of encodings, names, and enrollment numbers to `.npy` files inside the `encodings/` directory.

### 3.2 Marking Attendance (`attendance.py`)
1. **Synchronization**: Ensures any student in `students.csv` exists in `Attendance.csv`.
2. **Column Initialization**: Detects if a column for the current date (e.g., `YYYY-MM-DD`) exists. If not, initializes it with empty cells.
3. **Locking**: Acquires a `filelock` (`attendance.lock`) before modifying the file to avoid race conditions.
4. **Attendance Logging**: Sets the cells matching the recognized student and current date to the current timestamp. Ignores already marked students.

### 3.3 Absentee Marking (`mark_absent.py`)
1. Scans `Attendance.csv` for the current date's column.
2. Identifies any students whose attendance is blank (`""`).
3. Marks them as `"Absent"`.

---

## 📝 4. Setup & Running Instructions

### 1. Install Dependencies
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Local Folders
Create `images/` and `encodings/` folders in the root directory:
```bash
mkdir images encodings
```
Place student portrait photos in `images/` named exactly after their enrollment IDs (e.g. `CI-152.jpeg`).

### 3. Update students.csv
Add student rows:
```csv
enrollment_no,name,image_filename
CI-152,Mohit Ojha,CI-152.jpeg
```

### 4. Run the Application
* **Web UI (Streamlit):**
  ```bash
  streamlit run app.py
  ```
  *(Press "Encode Faces" in sidebar, then Start Webcam to begin).*
* **Terminal Mode (OpenCV):**
  ```bash
  python encode.py
  python decode.py
  ```
