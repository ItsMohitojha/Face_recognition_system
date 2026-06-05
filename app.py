import streamlit as st
import logging
import os
import csv
import numpy as np
import cv2
import face_recognition
from datetime import datetime
import pandas as pd
import threading
import queue
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
from attendance import mark_attendance, initialize_attendance_file, mark_absent_students
import av
import config

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger()

# Suppress verbose WebRTC logs
logging.getLogger('streamlit_webrtc').setLevel(logging.WARNING)
logging.getLogger('aiortc').setLevel(logging.WARNING)

# Global queue for thread-safe logging
log_queue = queue.Queue()

# Custom logging handler for Streamlit using queue
class StreamlitHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        log_queue.put(msg)

# Video processor class
class VideoProcessor:
    def __init__(self):
        self.known_face_encodings = None
        self.known_face_names = None
        self.known_face_enrollments = None
        self.load_encodings()

    def load_encodings(self):
        try:
            self.known_face_encodings = np.load(os.path.join(config.ENCODINGS_DIR, 'known_encodings.npy'))
            self.known_face_names = np.load(os.path.join(config.ENCODINGS_DIR, 'names.npy'))
            self.known_face_enrollments = np.load(os.path.join(config.ENCODINGS_DIR, 'enrollment_nos.npy'))
            logging.info("✅ Successfully loaded known faces and encodings.")
        except FileNotFoundError:
            logging.error("🚨 Encoding files not found! Please encode faces first.")

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        img_rgb_small = cv2.resize(img, (0, 0), fx=0.25, fy=0.25)
        face_locations = face_recognition.face_locations(img_rgb_small)
        face_encodings = face_recognition.face_encodings(img_rgb_small, face_locations)

        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
            face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
            best_match_index = np.argmin(face_distances)

            if matches[best_match_index]:
                name = self.known_face_names[best_match_index]
                enrollment = self.known_face_enrollments[best_match_index]
                top, right, bottom, left = [coord * 4 for coord in (top, right, bottom, left)]
                cv2.rectangle(img, (left, top), (right, bottom), (0, 255, 0), 2)
                cv2.rectangle(img, (left, bottom - 35), (right, bottom), (0, 255, 0), cv2.FILLED)
                cv2.putText(img, name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_COMPLEX, 0.8, (255, 255, 255), 2)
                mark_attendance(name, enrollment)
            else:
                logging.info("🕵️ Detected an unknown face.")
                top, right, bottom, left = [coord * 4 for coord in (top, right, bottom, left)]
                cv2.rectangle(img, (left, top), (right, bottom), (0, 0, 255), 2)
                cv2.rectangle(img, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
                cv2.putText(img, "Unknown", (left + 6, bottom - 6), cv2.FONT_HERSHEY_COMPLEX, 0.8, (255, 255, 255), 2)

        return av.VideoFrame.from_ndarray(img, format="bgr24")

# Function to run encoding in a thread
def run_encode():
    try:
        known_encodings = []
        known_names = []
        known_enrollments = []

        logging.info("⚙️ Starting to encode faces from students.csv...")

        if not os.path.exists(config.STUDENTS_FILE):
             logging.error(f"❌ {config.STUDENTS_FILE} not found.")
             return

        with open(config.STUDENTS_FILE, mode='r') as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                enrollment_no = row['enrollment_no'].strip()
                name = row['name'].strip()
                image_filename = row['image_filename'].strip()
                
                img_path = os.path.join(config.IMAGES_DIR, image_filename)

                if not os.path.exists(img_path):
                    logging.warning(f"⚠️ Image file '{image_filename}' not found for {name}. Skipping...")
                    continue

                img = cv2.imread(img_path)
                if img is None:
                    logging.warning(f"⚠️ Could not read image file '{image_filename}'. Skipping...")
                    continue
                
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                face_locations = face_recognition.face_locations(img_rgb)
                
                if len(face_locations) > 0:
                    encode = face_recognition.face_encodings(img_rgb, face_locations)[0]
                    known_encodings.append(encode)
                    known_names.append(name)
                    known_enrollments.append(enrollment_no)
                    logging.info(f"👍 Encoding successful for: {name} ({enrollment_no})")
                else:
                    logging.warning(f"🧐 No face found in '{image_filename}' for {name}. Skipping.")

        if len(known_encodings) > 0:
            logging.info(f"✨ Encoding Complete. Found {len(known_encodings)} faces.")

            if not os.path.exists(config.ENCODINGS_DIR):
                os.makedirs(config.ENCODINGS_DIR)
                
            np.save(os.path.join(config.ENCODINGS_DIR, 'known_encodings.npy'), known_encodings)
            np.save(os.path.join(config.ENCODINGS_DIR, 'names.npy'), known_names)
            np.save(os.path.join(config.ENCODINGS_DIR, 'enrollment_nos.npy'), known_enrollments)
            
            logging.info("💾 Successfully saved all encoding data.")
        else:
            logging.error("❌ Encoding Failed: No faces were encoded.")
    except Exception as e:
        logging.error(f"Error during encoding: {e}")

# Function to run mark absents in a thread
def run_mark_absent():
    try:
        logging.info("📋 Starting process to mark all unattended students as 'Absent'.")
        mark_absent_students()
        logging.info("✅ Absentee marking process complete.")
    except Exception as e:
        logging.error(f"Error marking absents: {e}")

# Main Streamlit app
def main():
    st.set_page_config(page_title="Stitch Attendance", layout="wide", page_icon="🧵")

    # Custom CSS for Stitch UI
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Outfit:wght@500;700&display=swap');

    /* Global Typography & Background */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: hsl(0, 0%, 90%);
    }

    /* Set overall background color for the dark mode */
    .stApp {
        background-color: hsl(220, 20%, 10%);
    }

    /* Headings */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', sans-serif;
        color: hsl(0, 0%, 100%);
    }

    /* Main Title Styling */
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        background: linear-gradient(90deg, hsl(230, 80%, 70%), hsl(280, 80%, 70%));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    /* Glassmorphism Containers */
    .glass-container {
        background: hsla(220, 20%, 20%, 0.4);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid hsla(220, 20%, 40%, 0.3);
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 8px 32px 0 hsla(0, 0%, 0%, 0.3);
        margin-bottom: 1.5rem;
    }

    /* Metrics Cards */
    .metric-card {
        background: hsla(220, 20%, 20%, 0.4);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid hsla(220, 20%, 40%, 0.3);
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 4px 16px 0 hsla(0, 0%, 0%, 0.2);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 24px 0 hsla(0, 0%, 0%, 0.4);
    }
    .metric-title {
        font-size: 1rem;
        font-weight: 500;
        color: hsl(220, 10%, 70%);
        margin-bottom: 0.5rem;
    }
    .metric-value {
        font-family: 'Outfit', sans-serif;
        font-size: 2.5rem;
        font-weight: 700;
        color: hsl(0, 0%, 100%);
    }

    /* Stylish Buttons */
    .stButton>button {
        background: linear-gradient(135deg, hsl(230, 70%, 60%), hsl(280, 70%, 60%));
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        font-family: 'Inter', sans-serif;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px hsla(230, 70%, 60%, 0.3);
        width: 100%;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px hsla(230, 70%, 60%, 0.5);
        color: white;
        border: none;
    }
    .stButton>button:active {
        transform: translateY(0);
    }

    /* Input fields and tables styling */
    .stTextInput>div>div>input {
        background-color: hsla(220, 20%, 15%, 0.8);
        color: white;
        border: 1px solid hsla(220, 20%, 30%, 0.5);
        border-radius: 8px;
    }
    .stTextInput>div>div>input:focus {
        border-color: hsl(230, 70%, 60%);
        box-shadow: 0 0 0 1px hsl(230, 70%, 60%);
    }

    /* Sidebar customization */
    [data-testid="stSidebar"] {
        background-color: hsl(220, 20%, 12%);
        border-right: 1px solid hsla(220, 20%, 30%, 0.3);
    }

    /* Text Area (Logs) */
    .stTextArea>div>div>textarea {
        background-color: hsla(220, 20%, 15%, 0.8);
        color: hsl(120, 60%, 70%); /* Matrix-like green for logs */
        font-family: monospace;
        border: 1px solid hsla(220, 20%, 30%, 0.5);
        border-radius: 8px;
    }

    /* Dataframe styling overrides for dark theme */
    [data-testid="stDataFrame"] {
        background-color: transparent;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="main-title">Face Recognition Attendance System</div>', unsafe_allow_html=True)

    # Initialize session state for logs
    if 'logs' not in st.session_state:
        st.session_state.logs = []

    # Drain queue
    while not log_queue.empty():
        st.session_state.logs.append(log_queue.get())

    # Remove existing StreamlitHandlers if any
    for h in logger.handlers[:]:
        if isinstance(h, StreamlitHandler):
            logger.removeHandler(h)

    # Add handler only once
    if 'logging_configured' not in st.session_state:
        handler = StreamlitHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
        logger.addHandler(handler)
        st.session_state.logging_configured = True

    # Calculate Statistics
    total_students = 0
    present_students = 0
    absent_students = 0
    today_str = datetime.now().strftime(config.DATE_FORMAT)

    if os.path.exists(config.STUDENTS_FILE):
        with open(config.STUDENTS_FILE, mode='r') as infile:
            total_students = sum(1 for row in csv.reader(infile)) - 1  # -1 for header

    if os.path.exists(config.ATTENDANCE_FILE):
        df_att = pd.read_csv(config.ATTENDANCE_FILE)
        if today_str in df_att.columns:
            present_students = df_att[df_att[today_str].notna() & (df_att[today_str] != '') & (df_att[today_str] != 'Absent')].shape[0]
            absent_students = df_att[df_att[today_str] == 'Absent'].shape[0]

    # Statistics Dashboard
    st.markdown("<h3>Today's Statistics</h3>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f'''
        <div class="metric-card">
            <div class="metric-title">Total Students</div>
            <div class="metric-value">{total_students}</div>
        </div>
        ''', unsafe_allow_html=True)

    with col2:
        st.markdown(f'''
        <div class="metric-card">
            <div class="metric-title">Present</div>
            <div class="metric-value" style="color: hsl(120, 60%, 60%);">{present_students}</div>
        </div>
        ''', unsafe_allow_html=True)

    with col3:
        st.markdown(f'''
        <div class="metric-card">
            <div class="metric-title">Absent</div>
            <div class="metric-value" style="color: hsl(0, 60%, 60%);">{absent_students}</div>
        </div>
        ''', unsafe_allow_html=True)

    # Log display
    st.markdown("---")
    st.markdown("<h3>System Logs</h3>", unsafe_allow_html=True)
    st.text_area("Logs display", value='\n'.join(st.session_state.logs), height=150, disabled=True, label_visibility="collapsed")
    col_log1, col_log2 = st.columns([1, 1])
    with col_log1:
        if st.button("Refresh Logs"):
            pass  # Triggers rerun to update logs
    with col_log2:
        if st.button("Clear Logs"):
            st.session_state.logs = []
            st.rerun()

    # Sidebar for controls
    with st.sidebar:
        st.markdown("<h3 style='margin-bottom: 1rem;'>Controls</h3>", unsafe_allow_html=True)
        if st.button("📷 Encode Faces"):
            with st.spinner("Encoding faces..."):
                run_encode()

        if st.button("📝 Mark Absents"):
            with st.spinner("Marking absents..."):
                run_mark_absent()


    # Webcam streaming
    st.markdown("---")
    st.markdown("<h3>Live Attendance Webcam</h3>", unsafe_allow_html=True)

    ctx = webrtc_streamer(
        key="attendance",
        mode=WebRtcMode.SENDRECV,
        rtc_configuration=RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}),
        video_processor_factory=VideoProcessor,
        async_processing=True,
    )

    # Log session state only if changed
    if 'was_playing' not in st.session_state:
        st.session_state.was_playing = False

    if ctx.state.playing != st.session_state.was_playing:
        if ctx.state.playing:
            logging.info("🚀 Starting attendance session...")
        else:
            logging.info("🛑 Attendance session stopped.")
        st.session_state.was_playing = ctx.state.playing

    # Clean, Searchable Data Table
    st.markdown("---")
    st.markdown("<h3>Attendance Logs</h3>", unsafe_allow_html=True)

    if os.path.exists(config.ATTENDANCE_FILE):
        df = pd.read_csv(config.ATTENDANCE_FILE)

        # Search Functionality
        search_query = st.text_input("🔍 Search by Name or Enrollment No", "")

        if search_query:
            # Case-insensitive search across 'Name' and 'Enrollment' columns
            mask = df['Name'].astype(str).str.contains(search_query, case=False, na=False) | \
                   df['Enrollment'].astype(str).str.contains(search_query, case=False, na=False)
            filtered_df = df[mask]
        else:
            filtered_df = df

        st.dataframe(filtered_df, use_container_width=True)
    else:
        st.info("No attendance data available yet. Attendance.csv not found.")


if __name__ == "__main__":
    main()