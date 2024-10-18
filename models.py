#This file will contain the Reminder class, which represents individual reminders.

#models.py:
# Contains the Reminder class.
# Represents the data model for reminders.

from datetime import datetime

class Reminder:
    def __init__(self, reminder_id, text, datetime_str, recurrence=None, recurrence_interval=1, recurrence_end=None):
        self.id = reminder_id
        self.text = text
        self.datetime_str = datetime_str  # Stored as a string for database compatibility
        self.datetime = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')  # Convert to datetime object
        self.recurrence = recurrence
        self.recurrence_interval = recurrence_interval
        self.recurrence_end = recurrence_end

    def __repr__(self):
        return f"<Reminder(id={self.id}, text='{self.text}', datetime='{self.datetime_str}', recurrence='{self.recurrence}', interval={self.recurrence_interval}, end='{self.recurrence_end}')>"


