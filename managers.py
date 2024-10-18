#This file will contain the ReminderManager, Notifier, and Scheduler classes, as well as any helper functions needed by these classes.

#models.py:
# Contains the Reminder class.
# Represents the data model for reminders.


import sqlite3
import threading
import time
import schedule
import logging
from datetime import datetime, timedelta
from win10toast import ToastNotifier
from models import Reminder

# Configure logging (if not already configured)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("reminder_bot.log"),
        logging.StreamHandler()
    ]
)

# Helper functions for date calculations
def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(
        sourcedate.day,
        [
            31,
            29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
            31,
            30,
            31,
            30,
            31,
            31,
            30,
            31,
            30,
            31
        ][month - 1]
    )
    return datetime(year, month, day, sourcedate.hour, sourcedate.minute, sourcedate.second)

def add_years(sourcedate, years):
    try:
        return sourcedate.replace(year=sourcedate.year + years)
    except ValueError:
        # Handle February 29 for leap years
        return sourcedate.replace(month=2, day=28, year=sourcedate.year + years)

class ReminderManager:
    def __init__(self, database):
        self.conn = sqlite3.connect(database, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_table()
    
    def create_table(self):
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY,
            text TEXT NOT NULL,
            datetime TEXT NOT NULL,
            recurrence TEXT DEFAULT NULL,
            recurrence_interval INTEGER DEFAULT 1,
            recurrence_end TEXT DEFAULT NULL
        )
        ''')
        self.conn.commit()
        logging.info("Database connected and table ensured.")
    
    def add_reminder(self, reminder):
        try:
            self.cursor.execute('''
            INSERT INTO reminders (text, datetime, recurrence, recurrence_interval, recurrence_end)
            VALUES (?, ?, ?, ?, ?)
            ''', (reminder.text, reminder.datetime_str, reminder.recurrence, reminder.recurrence_interval, reminder.recurrence_end))
            self.conn.commit()
            logging.info("Added reminder: '%s' at %s", reminder.text, reminder.datetime)
            print(f"Reminder set for {reminder.datetime.strftime('%b %d %Y %I:%M %p')}")
        except Exception as e:
            logging.error("Error adding reminder: %s", e)
            print("An error occurred while adding the reminder.")
    
    def get_due_reminders(self):
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.cursor.execute('SELECT * FROM reminders WHERE datetime <= ?', (now,))
        reminders = self.cursor.fetchall()
        return [self._create_reminder_from_row(row) for row in reminders]
    
    def update_reminder(self, reminder):
        try:
            self.cursor.execute('''
            UPDATE reminders
            SET text = ?, datetime = ?, recurrence = ?, recurrence_interval = ?, recurrence_end = ?
            WHERE id = ?
            ''', (reminder.text, reminder.datetime_str, reminder.recurrence, reminder.recurrence_interval, reminder.recurrence_end, reminder.id))
            self.conn.commit()
            logging.info("Updated reminder ID %d", reminder.id)
        except Exception as e:
            logging.error("Error updating reminder: %s", e)
    
    def delete_reminder(self, reminder_id):
        try:
            self.cursor.execute('DELETE FROM reminders WHERE id = ?', (reminder_id,))
            self.conn.commit()
            logging.info("Deleted reminder ID %d", reminder_id)
        except Exception as e:
            logging.error("Error deleting reminder: %s", e)
    
    def get_upcoming_reminders(self):
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.cursor.execute('SELECT * FROM reminders WHERE datetime > ? ORDER BY datetime ASC', (now,))
        reminders = self.cursor.fetchall()
        return [self._create_reminder_from_row(row) for row in reminders]
    
    def _create_reminder_from_row(self, row):
        return Reminder(
            reminder_id=row[0],
            text=row[1],
            datetime_str=row[2],
            recurrence=row[3],
            recurrence_interval=row[4],
            recurrence_end=row[5]
        )
    
    def close(self):
        self.conn.close()
        logging.info("Database connection closed.")

class Notifier:
    def __init__(self):
        self.toaster = ToastNotifier()
    
    def send_notification(self, message):
        try:
            self.toaster.show_toast(
                "Reminder",
                message,
                duration=10,
                threaded=True
            )
            while self.toaster.notification_active():
                time.sleep(0.1)
            logging.info("Notification sent: '%s'", message)
        except Exception as e:
            logging.error("Failed to send notification: %s", e)

class Scheduler:
    def __init__(self, reminder_manager, notifier):
        self.reminder_manager = reminder_manager
        self.notifier = notifier
        schedule.every(1).minutes.do(self.check_reminders)
    
    def start(self):
        self.scheduler_thread = threading.Thread(target=self.run, daemon=True)
        self.scheduler_thread.start()
    
    def run(self):
        while True:
            schedule.run_pending()
            time.sleep(1)
    
    def check_reminders(self):
        try:
            due_reminders = self.reminder_manager.get_due_reminders()
            for reminder in due_reminders:
                self.notifier.send_notification(reminder.text)
                if reminder.recurrence:
                    next_datetime = self.calculate_next_occurrence(reminder)
                    if next_datetime:
                        reminder.datetime = next_datetime
                        reminder.datetime_str = next_datetime.strftime('%Y-%m-%d %H:%M:%S')
                        self.reminder_manager.update_reminder(reminder)
                    else:
                        self.reminder_manager.delete_reminder(reminder.id)
                else:
                    self.reminder_manager.delete_reminder(reminder.id)
        except Exception as e:
            logging.error("Error checking reminders: %s", e)
    
    def calculate_next_occurrence(self, reminder):
        # Calculate the next occurrence based on the recurrence pattern
        current_datetime = reminder.datetime
        recurrence_interval = reminder.recurrence_interval
        if reminder.recurrence == 'daily':
            next_datetime = current_datetime + timedelta(days=recurrence_interval)
        elif reminder.recurrence == 'weekly':
            next_datetime = current_datetime + timedelta(weeks=recurrence_interval)
        elif reminder.recurrence == 'monthly':
            next_datetime = add_months(current_datetime, recurrence_interval)
        elif reminder.recurrence == 'yearly':
            next_datetime = add_years(current_datetime, recurrence_interval)
        else:
            logging.warning("Unknown recurrence pattern: '%s'", reminder.recurrence)
            return None
        
        if reminder.recurrence_end:
            recurrence_end_datetime = datetime.strptime(reminder.recurrence_end, '%Y-%m-%d %H:%M:%S')
            if next_datetime > recurrence_end_datetime:
                logging.info("Recurring reminder ended: ID %d", reminder.id)
                return None  # Recurrence has ended
        
        return next_datetime
