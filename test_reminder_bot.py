import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
import reminder_bot
from freezegun import freeze_time

# Adjusted local timezone
LOCAL_TZ = timezone(timedelta(hours=3))  # Replace with your actual local timezone offset

@pytest.fixture
def mock_database():
    with patch('sqlite3.connect') as mock_connect:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Override conn and cursor in reminder_bot.py
        reminder_bot.conn = mock_conn
        reminder_bot.cursor = mock_cursor

        yield mock_conn, mock_cursor

@pytest.fixture
def mock_send_notification():
    with patch('reminder_bot.send_notification') as mock_notification:
        yield mock_notification

@pytest.fixture
def mock_print():
    with patch('builtins.print') as mock_print:
        yield mock_print

@freeze_time("2022-01-01 12:00:00", tz_offset=3)
def test_add_reminder_success(mock_database, mock_send_notification, mock_print):
    mock_conn, mock_cursor = mock_database
    inputs = ['Test Reminder', 'in 10 minutes', 'n']
    with patch('builtins.input', side_effect=inputs):
        reminder_bot.add_reminder()

    # Assert that the reminder was inserted into the database
    mock_cursor.execute.assert_called_once()

    # Check that the correct SQL command was executed
    args, kwargs = mock_cursor.execute.call_args
    assert 'INSERT INTO reminders' in args[0]

    # Verify that the reminder was scheduled for the correct time
    inserted_datetime_str = args[1][1]
    inserted_datetime = datetime.strptime(inserted_datetime_str, '%Y-%m-%d %H:%M:%S')

    # Expected datetime should be adjusted for tz_offset
    expected_datetime = datetime(2022, 1, 1, 12, 10, 0)
    assert inserted_datetime == expected_datetime

    # Check that the user was notified of the successful addition
    mock_print.assert_any_call(f"Reminder set for {inserted_datetime.strftime('%b %d %Y %I:%M %p')}")

@freeze_time("2022-01-01 12:00:00", tz_offset=3)
def test_add_reminder_past_time(mock_database, mock_send_notification, mock_print):
    mock_conn, mock_cursor = mock_database
    inputs = ['Test Reminder', '10 minutes ago']
    with patch('builtins.input', side_effect=inputs):
        reminder_bot.add_reminder()

    # Ensure no database operations were performed
    mock_cursor.execute.assert_not_called()
    mock_conn.commit.assert_not_called()
    # Check that the user was informed of the past time
    mock_print.assert_any_call("The time you entered is in the past. Please enter a future time.")

@freeze_time("2022-01-01 12:00:00", tz_offset=3)
def test_add_reminder_invalid_time(mock_database, mock_send_notification, mock_print):
    mock_conn, mock_cursor = mock_database
    inputs = ['Test Reminder', 'invalid time']
    with patch('builtins.input', side_effect=inputs):
        reminder_bot.add_reminder()

    # Ensure no database operations were performed
    mock_cursor.execute.assert_not_called()
    mock_conn.commit.assert_not_called()
    # Check that the user was informed of the invalid time
    mock_print.assert_any_call("Sorry, I didn't understand the time you entered.")
    mock_print.assert_any_call("Try phrases like 'in 2 hours', 'next Friday at noon', or 'tomorrow evening'.")
