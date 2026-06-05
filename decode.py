import cv2
import numpy as np
import face_recognition
import os
import logging
from attendance import mark_attendance
from datetime import datetime

# Configure Logging with a fun format
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(message)s', # Simplified format to let emojis stand out
                    datefmt='%Y-%m-%d %H:%M:%S')

# --- Load Encodings ---
try:
    encodings_path = 'encodings'
    known_face_encodings = np.load(os.path.join(encodings_path, 'known_encodings.npy'))
    known_face_names = np.load(os.path.join(encodings_path, 'names.npy'))
    known_face_enrollments = np.load(os.path.join(encodings_path, 'enrollment_nos.npy'))
    logging.info("✅ Successfully loaded known faces and encodings.")
except FileNotFoundError:
    logging.info("🚨 Encoding files not found! Please run 'encode.py' first.")
    exit()

# --- Initialize Webcam ---
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    logging.info("📸 Could not open webcam.")
    exit()

logging.info("🚀 Starting attendance session... Press 'Enter' to exit.")

while True:
    success, img = cap.read()
    if not success:
        logging.error("❌ Failed to capture frame from webcam. Exiting.")
        break

    imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
    imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)

    facesCurFrame = face_recognition.face_locations(imgS)
    encodesCurFrame = face_recognition.face_encodings(imgS, facesCurFrame)

    for encodeFace, faceLoc in zip(encodesCurFrame, facesCurFrame):
        matches = face_recognition.compare_faces(known_face_encodings, encodeFace)
        faceDis = face_recognition.face_distance(known_face_encodings, encodeFace)
        
        matchIndex = np.argmin(faceDis)

        if matches[matchIndex]:
            name = known_face_names[matchIndex]
            enrollment = known_face_enrollments[matchIndex]
            
            y1, x2, y2, x1 = faceLoc
            y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
            
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.rectangle(img, (x1, y2 - 35), (x2, y2), (0, 255, 0), cv2.FILLED)
            cv2.putText(img, name, (x1 + 6, y2 - 6), cv2.FONT_HERSHEY_COMPLEX, 0.8, (255, 255, 255), 2)
            
            mark_attendance(name, enrollment)
        else:
            # Handle unknown face
            logging.info("🕵️ Detected an unknown face.")
            y1, x2, y2, x1 = faceLoc
            y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
            
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)  # Red box
            cv2.rectangle(img, (x1, y2 - 35), (x2, y2), (0, 0, 255), cv2.FILLED)
            cv2.putText(img, "Unknown", (x1 + 6, y2 - 6), cv2.FONT_HERSHEY_COMPLEX, 0.8, (255, 255, 255), 2)

    cv2.imshow('Attendance System', img)
    
    if cv2.waitKey(1) == 13: # Enter key
        break

cap.release()
cv2.destroyAllWindows()
logging.info("🛑 Attendance session ended.")