#This file will contain the user interface functions and the main() function. It will import the classes from models.py and managers.py.

#main.py
# Contains the user interface functions (add_reminder_ui, view_reminders_ui, etc.).
# Contains the main() function, which initializes the classes and starts the program loop.
# Manages user interaction and ties everything together.

import logging
from datetime import datetime
import parsedatetime

from models import Reminder
from managers import ReminderManager, Notifier, Scheduler

# Initialize parsedatetime Calendar
cal = parsedatetime.Calendar()

# Configure logging (if not already configured)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("reminder_bot.log"),
        logging.StreamHandler()
    ]
)

def get_recurrence_info(reminder):
    if reminder.recurrence:
        recurrence_info = f" (Repeats every {reminder.recurrence_interval} {reminder.recurrence}"
        if reminder.recurrence_interval > 1:
            recurrence_info += "s"
        recurrence_info += ")"
        if reminder.recurrence_end:
            recurrence_info += f", until {datetime.strptime(reminder.recurrence_end, '%Y-%m-%d %H:%M:%S').strftime('%b %d %Y')}"
        return recurrence_info
    return ""

def get_recurrence_details():
    recurrence = input("Enter the recurrence pattern ('daily', 'weekly', 'monthly', 'yearly'): ").lower()
    if recurrence not in ('daily', 'weekly', 'monthly', 'yearly'):
        print("Invalid recurrence pattern. Setting as one-time reminder.")
        return None, 1, None

    recurrence_interval_input = input("Enter the interval (e.g., '1' for every day): ")
    try:
        recurrence_interval = int(recurrence_interval_input)
        if recurrence_interval < 1:
            print("Invalid interval. Setting interval to 1.")
            recurrence_interval = 1
    except ValueError:
        print("Invalid interval. Setting interval to 1.")
        recurrence_interval = 1

    recurrence_end_input = input("Enter the end date for recurrence (leave blank for no end date): ")
    if recurrence_end_input.strip() == '':
        recurrence_end = None
    else:
        end_time_struct, end_parse_status = cal.parse(recurrence_end_input)
        if end_parse_status == 0:
            print("Invalid end date. No end date will be set.")
            recurrence_end = None
        else:
            recurrence_end_datetime = datetime(*end_time_struct[:6])
            if recurrence_end_datetime <= datetime.now():
                print("The recurrence end date is in the past. No end date will be set.")
                recurrence_end = None
            else:
                recurrence_end = recurrence_end_datetime.strftime('%Y-%m-%d %H:%M:%S')

    return recurrence, recurrence_interval, recurrence_end

def add_reminder_ui(reminder_manager):
    try:
        reminder_text = input("What would you like to be reminded about? ")
        reminder_time = input("When should I remind you? (e.g., 'in 15 minutes', 'tomorrow at 5 pm'): ")
        time_struct, parse_status = cal.parse(reminder_time)
        if parse_status == 0:
            logging.warning("Failed to parse the reminder time: '%s'", reminder_time)
            print("Sorry, I didn't understand the time you entered.")
            return
        else:
            reminder_datetime = datetime(*time_struct[:6])
            if reminder_datetime <= datetime.now():
                print("The time you entered is in the past. Please enter a future time.")
                return

        recurrence = None
        recurrence_interval = 1
        recurrence_end = None

        recurrence_choice = input("Do you want this reminder to recur? (y/n): ").lower()
        if recurrence_choice == 'y':
            recurrence, recurrence_interval, recurrence_end = get_recurrence_details()

        reminder = Reminder(
            reminder_id=None,  # Will be set by the database
            text=reminder_text,
            datetime_str=reminder_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            recurrence=recurrence,
            recurrence_interval=recurrence_interval,
            recurrence_end=recurrence_end
        )
        reminder_manager.add_reminder(reminder)
    except Exception as e:
        logging.error("Error adding reminder: %s", e)
        print("An error occurred while adding the reminder.")

def view_reminders_ui(reminder_manager):
    reminders = reminder_manager.get_upcoming_reminders()
    if not reminders:
        print("You have no upcoming reminders.")
    else:
        print("\nHere's your list of upcoming reminders:")
        for idx, reminder in enumerate(reminders, start=1):
            formatted_time = reminder.datetime.strftime('%b %d %Y %I:%M %p')
            recurrence_info = get_recurrence_info(reminder)
            print(f"{idx}. [{formatted_time}] - {reminder.text}{recurrence_info}")

def edit_reminder_ui(reminder_manager):
    try:
        reminders = reminder_manager.get_upcoming_reminders()
        if not reminders:
            print("You have no reminders to edit.")
            return

        print("\nSelect a reminder to edit:")
        for idx, reminder in enumerate(reminders, start=1):
            formatted_time = reminder.datetime.strftime('%b %d %Y %I:%M %p')
            recurrence_info = get_recurrence_info(reminder)
            print(f"{idx}. [{formatted_time}] - {reminder.text}{recurrence_info}")

        choice = int(input("Enter the number of the reminder to edit: "))
        if 1 <= choice <= len(reminders):
            selected_reminder = reminders[choice - 1]
            print("\nWhat would you like to edit?")
            print("1. Edit reminder text")
            print("2. Edit reminder time")
            print("3. Edit both text and time")
            print("4. Edit recurrence settings")
            print("5. Edit all (text, time, and recurrence)")
            edit_choice = input("Enter your choice (1-5): ")

            if edit_choice == '1':
                # Edit reminder text
                new_text = input("Enter the new reminder text: ")
                selected_reminder.text = new_text
                reminder_manager.update_reminder(selected_reminder)
                print("Reminder text updated successfully.")

            elif edit_choice == '2':
                # Edit reminder time
                new_time_input = input("Enter the new reminder time (e.g., 'in 2 hours'): ")
                time_struct, parse_status = cal.parse(new_time_input)
                if parse_status == 0:
                    print("Sorry, I didn't understand the time you entered.")
                else:
                    new_datetime = datetime(*time_struct[:6])
                    if new_datetime <= datetime.now():
                        print("The time you entered is in the past. Please enter a future time.")
                    else:
                        selected_reminder.datetime = new_datetime
                        selected_reminder.datetime_str = new_datetime.strftime('%Y-%m-%d %H:%M:%S')
                        reminder_manager.update_reminder(selected_reminder)
                        print("Reminder time updated successfully.")

            elif edit_choice == '3':
                # Edit both text and time
                new_text = input("Enter the new reminder text: ")
                new_time_input = input("Enter the new reminder time (e.g., 'tomorrow at 5pm'): ")
                time_struct, parse_status = cal.parse(new_time_input)
                if parse_status == 0:
                    print("Sorry, I didn't understand the time you entered.")
                else:
                    new_datetime = datetime(*time_struct[:6])
                    if new_datetime <= datetime.now():
                        print("The time you entered is in the past. Please enter a future time.")
                    else:
                        selected_reminder.text = new_text
                        selected_reminder.datetime = new_datetime
                        selected_reminder.datetime_str = new_datetime.strftime('%Y-%m-%d %H:%M:%S')
                        reminder_manager.update_reminder(selected_reminder)
                        print("Reminder text and time updated successfully.")

            elif edit_choice == '4':
                # Edit recurrence settings
                recurrence_choice = input("Do you want this reminder to recur? (y/n): ").lower()
                if recurrence_choice == 'y':
                    recurrence, recurrence_interval, recurrence_end = get_recurrence_details()
                    selected_reminder.recurrence = recurrence
                    selected_reminder.recurrence_interval = recurrence_interval
                    selected_reminder.recurrence_end = recurrence_end
                else:
                    # Remove recurrence
                    selected_reminder.recurrence = None
                    selected_reminder.recurrence_interval = 1
                    selected_reminder.recurrence_end = None
                reminder_manager.update_reminder(selected_reminder)
                print("Recurrence settings updated successfully.")

            elif edit_choice == '5':
                # Edit all (text, time, and recurrence)
                new_text = input("Enter the new reminder text: ")
                new_time_input = input("Enter the new reminder time (e.g., 'tomorrow at 5pm'): ")
                time_struct, parse_status = cal.parse(new_time_input)
                if parse_status == 0:
                    print("Sorry, I didn't understand the time you entered.")
                    return
                else:
                    new_datetime = datetime(*time_struct[:6])
                    if new_datetime <= datetime.now():
                        print("The time you entered is in the past. Please enter a future time.")
                        return
                # Edit recurrence settings
                recurrence_choice = input("Do you want this reminder to recur? (y/n): ").lower()
                if recurrence_choice == 'y':
                    recurrence, recurrence_interval, recurrence_end = get_recurrence_details()
                    selected_reminder.recurrence = recurrence
                    selected_reminder.recurrence_interval = recurrence_interval
                    selected_reminder.recurrence_end = recurrence_end
                else:
                    selected_reminder.recurrence = None
                    selected_reminder.recurrence_interval = 1
                    selected_reminder.recurrence_end = None

                selected_reminder.text = new_text
                selected_reminder.datetime = new_datetime
                selected_reminder.datetime_str = new_datetime.strftime('%Y-%m-%d %H:%M:%S')
                reminder_manager.update_reminder(selected_reminder)
                print("Reminder updated successfully.")

            else:
                print("Invalid choice. Returning to the main menu.")

        else:
            print("Invalid selection. Please enter a valid number.")

    except ValueError:
        print("Invalid input. Please enter a number.")
    except Exception as e:
        logging.error("Error editing reminder: %s", e)
        print("An error occurred while editing the reminder.")

def delete_reminder_ui(reminder_manager):
    reminders = reminder_manager.get_upcoming_reminders()
    if not reminders:
        print("You have no reminders to delete.")
        return

    print("\nSelect a reminder to delete:")
    for idx, reminder in enumerate(reminders, start=1):
        formatted_time = reminder.datetime.strftime('%b %d %Y %I:%M %p')
        recurrence_info = get_recurrence_info(reminder)
        print(f"{idx}. [{formatted_time}] - {reminder.text}{recurrence_info}")

    try:
        choice = int(input("Enter the number of the reminder to delete: "))
        if 1 <= choice <= len(reminders):
            selected_reminder = reminders[choice - 1]
            confirm = input(f"Are you sure you want to delete reminder '{selected_reminder.text}'? (y/n): ").lower()
            if confirm == 'y':
                reminder_manager.delete_reminder(selected_reminder.id)
                print("Reminder deleted successfully.")
            else:
                print("Deletion cancelled.")
        else:
            print("Invalid selection. Please enter a valid number.")
    except ValueError:
        print("Invalid input. Please enter a number.")

def main():
    reminder_manager = ReminderManager('reminders.db')
    notifier = Notifier()
    scheduler = Scheduler(reminder_manager, notifier)
    scheduler.start()

    try:
        while True:
            print("\nWhat would you like to do?")
            print("1. Add a new reminder")
            print("2. View upcoming reminders")
            print("3. Edit a reminder")
            print("4. Delete a reminder")
            print("5. Exit")
            choice = input("Enter your choice (1-5): ")

            if choice == '1':
                add_reminder_ui(reminder_manager)
            elif choice == '2':
                view_reminders_ui(reminder_manager)
            elif choice == '3':
                edit_reminder_ui(reminder_manager)  # Add this line
            elif choice == '4':
                delete_reminder_ui(reminder_manager)
            elif choice == '5':
                logging.info("User chose to exit the program.")
                print("Goodbye!")
                break
            else:
                logging.warning("Invalid menu choice: '%s'", choice)
                print("Invalid choice. Please try again.")
    except KeyboardInterrupt:
        logging.info("Program terminated by user.")
        print("\nExiting program.")
    except Exception as e:
        logging.critical("Unexpected error in main loop: %s", e)
        print("An unexpected error occurred. Exiting the program.")
    finally:
        reminder_manager.close()

if __name__ == "__main__":
    main()

