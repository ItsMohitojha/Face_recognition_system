import logging
from attendance import mark_absent_students

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

if __name__ == "__main__":
    logging.info("📋 Starting process to mark all unattended students as 'Absent'.")
    mark_absent_students()
    logging.info("✅ Absentee marking process complete.")