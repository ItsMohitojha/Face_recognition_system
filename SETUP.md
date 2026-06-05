# Setup Guide: Running the Project on a New Laptop

Follow these step-by-step instructions to set up and run this Face Recognition Attendance System on any laptop, starting from scratch.

---

## 💻 Step 1: Create a Folder and Open in VS Code
1. Create a new empty folder on your computer (e.g., `Face-Recognition-System`).
2. Open **VS Code**.
3. Go to the top menu: **File** ➔ **Open Folder...** and select your newly created folder.

---

## 📥 Step 2: Clone the Project Files
1. Open the integrated terminal in VS Code by pressing `Ctrl + ~` (or going to **Terminal** ➔ **New Terminal**).
2. Run the following command to clone all repository files into your open folder:
   ```bash
   git clone https://github.com/ItsMohitojha/Face_recognition_system.git .
   ```
   *(Note: The dot `.` at the end ensures the files clone directly into your current directory, not in a subdirectory).*

---

## 🐍 Step 3: Create & Activate a Python Virtual Environment
Creating a virtual environment ensures that the packages installed do not conflict with other Python projects on your machine.

1. **Create the environment:**
   ```bash
   python -m venv venv
   ```
2. **Activate the environment:**
   * **On Windows (PowerShell - default in VS Code):**
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
     *(If you get a script execution permission error, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in the terminal first).*
   * **On macOS / Linux:**
     ```bash
     source venv/bin/activate
     ```

*When activated, you will see `(venv)` appear at the beginning of your terminal command prompt.*

---

## 📦 Step 4: Install Dependencies
Run this command to install all required libraries (OpenCV, numpy, face_recognition, etc.):
```bash
pip install -r requirements.txt
```

---

## 🚀 Step 5: Run the System
Since the registered student photographs, master list, and pre-computed face encodings are already included in the cloned repository, you can start running it immediately!

### Option A: Run the Streamlit Web Dashboard
Streamlit provides a modern, clean web interface for managing the webcam, logs, and student statistics.
```bash
streamlit run app.py
```
*Your browser will automatically open the dashboard at `http://localhost:8501`.*

### Option B: Run Standalone Webcam Mode (OpenCV)
To run a simple local camera window without starting the web server:
```bash
python decode.py
```
*Press `Enter` in the camera frame to exit.*
