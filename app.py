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
    st.title("Face Recognition Attendance System")

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

    # Log display
    log_container = st.container()
    with log_container:
        st.subheader("Logs")
        st.text_area("Logs display", value='\n'.join(st.session_state.logs), height=200, disabled=True, label_visibility="collapsed")
        if st.button("Refresh Logs"):
            pass  # Triggers rerun to update logs
        if st.button("Clear Logs"):
            st.session_state.logs = []
            st.rerun()

    # Sidebar for controls
    with st.sidebar:
        st.header("Controls")
        if st.button("Encode Faces"):
            with st.spinner("Encoding faces..."):
                run_encode()

        if st.button("Mark Absents"):
            with st.spinner("Marking absents..."):
                run_mark_absent()

        if st.button("View Attendance"):
            if os.path.exists(config.ATTENDANCE_FILE):
                df = pd.read_csv(config.ATTENDANCE_FILE)
                st.dataframe(df)
            else:
                st.error("Attendance.csv not found.")

    # Webcam streaming
    st.header("Attendance Webcam")
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

if __name__ == "__main__":
    main()