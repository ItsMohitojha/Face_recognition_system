import csv
import os
import logging
from datetime import datetime
from filelock import FileLock
import config

logger = logging.getLogger(__name__)

def get_today_str():
    return datetime.now().strftime(config.DATE_FORMAT)

def get_current_time_str():
    return datetime.now().strftime(config.TIME_FORMAT)

def sync_students():
    """
    Ensures all students from students.csv are present in Attendance.csv.
    Preserves existing attendance data.
    """
    if not os.path.exists(config.STUDENTS_FILE):
        logger.error(f"❌ {config.STUDENTS_FILE} not found.")
        return

    students = {}
    with open(config.STUDENTS_FILE, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row['name'].strip(), row['enrollment_no'].strip())
            students[key] = True

    lock = FileLock(config.LOCK_FILE)
    with lock:
        if not os.path.exists(config.ATTENDANCE_FILE):
            # Create new file with all students
            try:
                with open(config.ATTENDANCE_FILE, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Name', 'Enrollment'])
                    for name, enrollment in students.keys():
                        writer.writerow([name, enrollment])
                logger.info(f"✅ Created {config.ATTENDANCE_FILE} with {len(students)} students.")
            except PermissionError:
                logger.error(f"🔒 Could not create {config.ATTENDANCE_FILE}.")
            return

        # File exists, sync it
        existing_data = []
        existing_students = set()
        headers = []

        try:
            with open(config.ATTENDANCE_FILE, 'r', newline='') as f:
                reader = list(csv.reader(f))
                if reader:
                    headers = reader[0]
                    existing_data = reader[1:]
                    for row in existing_data:
                        if len(row) >= 2:
                            existing_students.add((row[0].strip(), row[1].strip()))
        except FileNotFoundError:
             pass # Should not happen given check above

        # Identify new students
        new_students = []
        for student in students.keys():
            if student not in existing_students:
                new_students.append(student)

        if new_students:
            # Append new students
            # We need to pad them with empty strings for existing date columns
            num_date_cols = len(headers) - 2
            padding = [''] * num_date_cols
            
            try:
                with open(config.ATTENDANCE_FILE, 'a', newline='') as f:
                    writer = csv.writer(f)
                    for name, enrollment in new_students:
                        writer.writerow([name, enrollment] + padding)
                logger.info(f"➕ Added {len(new_students)} new students to attendance sheet.")
            except PermissionError:
                logger.error(f"🔒 Could not update {config.ATTENDANCE_FILE}.")

def initialize_attendance_file(today):
    """
    Ensures the attendance file exists, has all students, and has a column for today.
    """
    sync_students()

    lock = FileLock(config.LOCK_FILE)
    with lock:
        try:
            with open(config.ATTENDANCE_FILE, 'r', newline='') as f:
                reader = list(csv.reader(f))
        except FileNotFoundError:
             return # sync_students should have handled creation

        if not reader:
            return

        headers = reader[0]
        if today not in headers:
            headers.append(today)
            # Update headers and pad rows
            # We need to read everything, modify, and write back
            # Since we are inside a lock, this is safe from other processes using this lock
            
            updated_rows = [headers]
            for row in reader[1:]:
                row.append('') # Pad with empty string for new date
                updated_rows.append(row)
            
            try:
                with open(config.ATTENDANCE_FILE, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows(updated_rows)
                logger.info(f"📅 Added column for {today}.")
            except PermissionError:
                logger.error(f"🔒 Could not update {config.ATTENDANCE_FILE} with new date.")

def mark_attendance(name, enrollment):
    today = get_today_str()
    current_time = get_current_time_str()

    initialize_attendance_file(today)

    lock = FileLock(config.LOCK_FILE)
    with lock:
        try:
            with open(config.ATTENDANCE_FILE, 'r', newline='') as f:
                reader = list(csv.reader(f))
        except FileNotFoundError:
            return

        if not reader:
            return

        headers = reader[0]
        try:
            date_index = headers.index(today)
        except ValueError:
            logger.error(f"❌ Date {today} missing from headers even after initialization.")
            return

        student_found = False
        updated = False
        
        for row in reader[1:]:
            if row[0].strip() == name and row[1].strip() == enrollment:
                student_found = True
                if row[date_index] == '' or row[date_index] == 'Absent':
                    row[date_index] = current_time
                    updated = True
                    logger.info(f"✅ Attendance marked for {name} ({enrollment}).")
                break
        
        if not student_found:
            logger.warning(f"🤔 Student {name} ({enrollment}) not found in attendance sheet (try restarting to sync).")

        if updated:
            try:
                with open(config.ATTENDANCE_FILE, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows(reader)
            except PermissionError:
                logger.error(f"🔒 Could not write to {config.ATTENDANCE_FILE}.")

def mark_absent_students():
    today = get_today_str()
    initialize_attendance_file(today)

    lock = FileLock(config.LOCK_FILE)
    with lock:
        try:
            with open(config.ATTENDANCE_FILE, 'r', newline='') as f:
                reader = list(csv.reader(f))
        except FileNotFoundError:
            return

        if not reader:
            return

        headers = reader[0]
        try:
            date_index = headers.index(today)
        except ValueError:
            return

        updated = False
        absentees_marked = 0
        
        for row in reader[1:]:
            if len(row) > date_index and row[date_index] == '':
                row[date_index] = 'Absent'
                updated = True
                absentees_marked += 1
                logger.info(f"🚫 Marked Absent for {row[0]} ({row[1]}).")

        if absentees_marked == 0:
            logger.info("👍 No absentees to mark.")

        if updated:
            try:
                with open(config.ATTENDANCE_FILE, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows(reader)
            except PermissionError:
                logger.error(f"🔒 Could not write to {config.ATTENDANCE_FILE}.")