# Face Recognition Attendance System

An automated, real-time attendance system built with Python, Streamlit, OpenCV, and the `face_recognition` library. It detects and identifies student faces from a live webcam feed and records their attendance in a CSV sheet.

---

## 🚀 Setup Instructions

### 1. Prerequisites
Ensure you have Python 3.8+ installed on your system.

### 2. Prepare the Images Folder
> [!IMPORTANT]
> For privacy reasons, student photographs and serialized face encodings are **not** committed to the Git repository.
> 
> You must create an `images` folder at the root directory of this project and add student images there.
> - **Filename format:** Images should be named after the student's enrollment/roll number (e.g., `CI-135.jpeg`, `CI-152.jpeg`).
> - Supported formats: `.jpeg`, `.jpg`, `.png`.

### 3. Update the Student Database
Open `students.csv` and add your students with the following columns:
```csv
enrollment_no,name,image_filename
CI-135,Student Name,CI-135.jpeg
```

### 4. Install Dependencies
Create a Python virtual environment and install the required libraries:
```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

---

## 💻 Running the Application

### Option A: Web-based Interface (Streamlit)
The Web UI provides face encoding, real-time webcam streaming, and attendance log visualization.
1. Run the Streamlit server:
   ```bash
   streamlit run app.py
   ```
2. Open the URL provided in your browser.
3. Click **Encode Faces** in the sidebar to process the student pictures in the `images/` directory.
4. Use the webcam control to start marking attendance in real time.

### Option B: Standalone Mode (OpenCV Window)
A lightweight option to run the camera feed directly in an OpenCV window:
1. Generate face encodings:
   ```bash
   python encode.py
   ```
2. Start the attendance session:
   ```bash
   python decode.py
   ```
3. Press `Enter` in the video window to stop the session.

---

## 📊 How Attendance is Recorded
* The system checks the date and initializes a new column for the current date in `Attendance.csv`.
* Recognized faces mark the student with the current timestamp.
* You can mark all remaining students as **Absent** using the Streamlit controls or by running:
  ```bash
  python mark_absent.py
  ```
