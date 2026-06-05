import cv2
import numpy as np
import face_recognition
import os
import csv
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

path = 'images'
students_csv_file = 'students.csv'

known_encodings = []
known_names = []
known_enrollments = []

logging.info("⚙️ Starting to encode faces from students.csv...")

try:
    with open(students_csv_file, mode='r') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            enrollment_no = row['enrollment_no'].strip()
            name = row['name'].strip()
            image_filename = row['image_filename'].strip()
            
            img_path = os.path.join(path, image_filename)

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
                logging.info(f"✅ Encoding successful for: {name} ({enrollment_no})")
            else:
                logging.warning(f"🧐 No face found in '{image_filename}' for {name}. Skipping.")

except FileNotFoundError:
    logging.critical(f"🚨 {students_csv_file} not found. Please create it first.")
    exit()

if len(known_encodings) > 0:
    logging.info(f"✨ Encoding Complete. Found {len(known_encodings)} faces.")

    output_dir = 'encodings'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    np.save(f'{output_dir}/known_encodings.npy', known_encodings)
    np.save(f'{output_dir}/names.npy', known_names)
    np.save(f'{output_dir}/enrollment_nos.npy', known_enrollments)
    
    logging.info("💾 Successfully saved all encoding data.")
else:
    logging.error("❌ Encoding Failed: No faces were encoded.")