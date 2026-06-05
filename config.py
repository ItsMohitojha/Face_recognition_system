import os

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# File paths
ATTENDANCE_FILE = os.path.join(BASE_DIR, 'Attendance.csv')
STUDENTS_FILE = os.path.join(BASE_DIR, 'students.csv')
ENCODINGS_DIR = os.path.join(BASE_DIR, 'encodings')
IMAGES_DIR = os.path.join(BASE_DIR, 'images')

# Date formats
DATE_FORMAT = '%Y-%m-%d'
TIME_FORMAT = '%I:%M %p'

# Lock file
LOCK_FILE = os.path.join(BASE_DIR, 'attendance.lock')
