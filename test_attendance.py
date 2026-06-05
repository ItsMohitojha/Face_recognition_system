import unittest
import os
import csv
import shutil
import threading
import time
from datetime import datetime
import config
import attendance

class TestAttendance(unittest.TestCase):
    def setUp(self):
        # Backup existing files
        self.backup_dir = os.path.join(config.BASE_DIR, 'backup_test')
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
        
        if os.path.exists(config.ATTENDANCE_FILE):
            shutil.copy(config.ATTENDANCE_FILE, self.backup_dir)
        if os.path.exists(config.STUDENTS_FILE):
            shutil.copy(config.STUDENTS_FILE, self.backup_dir)
            
        # Create dummy students file
        with open(config.STUDENTS_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['enrollment_no', 'name', 'image_filename'])
            writer.writerow(['TEST001', 'Test Student 1', 'test1.jpg'])
            writer.writerow(['TEST002', 'Test Student 2', 'test2.jpg'])

        # Remove attendance file if exists
        if os.path.exists(config.ATTENDANCE_FILE):
            os.remove(config.ATTENDANCE_FILE)

    def tearDown(self):
        # Restore files
        if os.path.exists(config.ATTENDANCE_FILE):
            os.remove(config.ATTENDANCE_FILE)
            
        if os.path.exists(os.path.join(self.backup_dir, 'Attendance.csv')):
            shutil.copy(os.path.join(self.backup_dir, 'Attendance.csv'), config.ATTENDANCE_FILE)
        
        if os.path.exists(os.path.join(self.backup_dir, 'students.csv')):
            shutil.copy(os.path.join(self.backup_dir, 'students.csv'), config.STUDENTS_FILE)
            
        shutil.rmtree(self.backup_dir)

    def test_initialization(self):
        today = datetime.now().strftime(config.DATE_FORMAT)
        attendance.initialize_attendance_file(today)
        
        self.assertTrue(os.path.exists(config.ATTENDANCE_FILE))
        
        with open(config.ATTENDANCE_FILE, 'r') as f:
            reader = list(csv.reader(f))
            self.assertEqual(len(reader), 3) # Header + 2 students
            self.assertIn(today, reader[0])

    def test_mark_attendance(self):
        attendance.mark_attendance('Test Student 1', 'TEST001')
        
        with open(config.ATTENDANCE_FILE, 'r') as f:
            reader = list(csv.reader(f))
            headers = reader[0]
            today = datetime.now().strftime(config.DATE_FORMAT)
            date_index = headers.index(today)
            
            for row in reader[1:]:
                if row[0] == 'Test Student 1':
                    self.assertNotEqual(row[date_index], '')
                    self.assertNotEqual(row[date_index], 'Absent')

    def test_concurrency(self):
        def mark_worker(name, enrollment):
            for _ in range(10):
                attendance.mark_attendance(name, enrollment)
                time.sleep(0.01)

        t1 = threading.Thread(target=mark_worker, args=('Test Student 1', 'TEST001'))
        t2 = threading.Thread(target=mark_worker, args=('Test Student 2', 'TEST002'))
        
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        
        # Verify file integrity
        with open(config.ATTENDANCE_FILE, 'r') as f:
            reader = list(csv.reader(f))
            self.assertEqual(len(reader), 3)

if __name__ == '__main__':
    unittest.main()
