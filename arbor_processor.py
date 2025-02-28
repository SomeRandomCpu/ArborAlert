from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import re
import datetime
from time import sleep
from database import get_credentials, get_reminder_days, clear_user_reminders, add_reminder

# Process Arbor Data
def process_arbor_data(discord_id):
    username, password = get_credentials(discord_id)
    if not username or not password:
        raise Exception("No credentials found for this user.")

    driver = webdriver.Firefox()
    try:
        driver.get(os.getenv("arborurl"))

        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Email address']"))
        )
        email_input.send_keys(username)

        password_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder='Password']")
        password_input.send_keys(password)
        password_input.send_keys(Keys.RETURN)
        sleep(3)  # Wait for login to complete

        visible_text = driver.find_element(By.TAG_NAME, "body").text
        with open("arbor_text.txt", "w", encoding="utf-8") as file:
            file.write(visible_text)

        print("Text extracted successfully!")

    except Exception as e:
        print(f"An error occurred during Arbor processing: {e}")
        raise  # Re-raise the exception to be handled by the caller
    finally:
        driver.quit()

    process_document("arbor_text.txt", "arbor_processed_text.txt", discord_id)

# Process document function
def process_document(file_path, output_path, discord_id):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        start_index = content.find("Overdue Assignments")
        end_index = content.find("Submitted Assignments")
        if start_index == -1 or end_index == -1:
            print("Key phrases not found in the document.")
            return False

        content = content.replace("Overdue Assignments", "Overdue Assignments:")
        content = content.replace("Assignments that are due", "Assignments that are due:")
        start_index = content.find("Overdue Assignments:")
        processed_content = content[start_index + len("Overdue Assignments:"):end_index].strip()
        processed_content = processed_content.replace("Assignments that are due:", "", 1).strip()

        with open(output_path, "w", encoding="utf-8") as file:
            file.write(processed_content)

        print(f"Processed text saved to {output_path}")
        
        # Parse assignments and due dates for reminders
        parse_assignments_and_schedule(processed_content, discord_id)
        return True
    except Exception as e:
        print(f"Error processing document: {e}")
        return False

# Parse assignments and schedule reminders
def parse_assignments_and_schedule(content, discord_id):
    # Get user's reminder preference
    reminder_days = get_reminder_days(discord_id)
    
    # Clear existing reminders for this user
    clear_user_reminders(discord_id)
    
    # Parse assignments and due dates
    lines = content.split('\n')
    current_assignment = None
    subject_code = None
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:  # Skip empty lines
            i += 1
            continue
            
        # Look for assignment entries (format: "7X/Ar: Mask evaulation  (Due 25 Feb 2025)") 
        # Extract subject code and assignment name
        subject_match = re.match(r'^([\w\d]+/[\w\d]+):\s+(.+?)\s*\(Due\s+(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})\)', line)
        if subject_match:
            subject_code = subject_match.group(1)  # e.g., "7X/Ar"
            assignment_name = subject_match.group(2)  # e.g., "Mask evaulation"
            due_date_str = subject_match.group(3)  # e.g., "25 Feb 2025"
            current_assignment = f"{subject_code}: {assignment_name}"
            
            try:
                # Parse the due date
                due_date = datetime.datetime.strptime(due_date_str, '%d %b %Y')
                
                # Calculate reminder date
                reminder_date = due_date - datetime.timedelta(days=reminder_days)
                
                # Only schedule if the reminder date is in the future
                if reminder_date > datetime.datetime.now():
                    add_reminder(
                        discord_id, 
                        current_assignment, 
                        due_date.strftime('%Y-%m-%d'), 
                        reminder_date.strftime('%Y-%m-%d')
                    )
                    print(f"Scheduled reminder for {current_assignment} due on {due_date.strftime('%Y-%m-%d')}")
            except ValueError:
                print(f"Could not parse date: {due_date_str}")
            i += 1
            continue
        
        # Handle format where subject code and assignment are on one line and due date is on the next line
        # Format: "7X/Pc: Spring Term Hmk Project" followed by "Due: YYYY-MM-DD" on next line
        subject_line_match = re.match(r'^([\w\d]+/[\w\d]+):\s+(.+?)$', line)
        if subject_line_match and i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            # Check if next line has a due date in YYYY-MM-DD format
            due_date_match_iso = re.match(r'^Due:\s+(\d{4}-\d{2}-\d{2})$', next_line)
            if due_date_match_iso:
                subject_code = subject_line_match.group(1)  # e.g., "7X/Pc"
                assignment_name = subject_line_match.group(2)  # e.g., "Spring Term Hmk Project"
                due_date_str = due_date_match_iso.group(1)  # e.g., "2025-04-03"
                current_assignment = f"{subject_code}: {assignment_name}"
                
                try:
                    # Parse the ISO format date
                    due_date = datetime.datetime.strptime(due_date_str, '%Y-%m-%d')
                    
                    # Calculate reminder date
                    reminder_date = due_date - datetime.timedelta(days=reminder_days)
                    
                    # Only schedule if the reminder date is in the future
                    if reminder_date > datetime.datetime.now():
                        add_reminder(
                            discord_id, 
                            current_assignment, 
                            due_date_str, 
                            reminder_date.strftime('%Y-%m-%d')
                        )
                        print(f"Scheduled reminder for {current_assignment} due on {due_date_str}")
                    i += 2  # Skip both the subject line and the due date line
                    continue
                except ValueError:
                    print(f"Could not parse date: {due_date_str}")
        
        # Also handle the old format for backward compatibility
        if ' - ' in line and not line.startswith('Due') and not line.startswith('Set'):
            current_assignment = line
        
        # Look for due dates in the old format
        due_date_match = re.search(r'Due:\s+(\d{1,2}/\d{1,2}/\d{4})', line)
        if current_assignment and due_date_match and not subject_match:
            due_date_str = due_date_match.group(1)
            try:
                # Parse the due date
                due_date = datetime.datetime.strptime(due_date_str, '%d/%m/%Y')
                
                # Calculate reminder date
                reminder_date = due_date - datetime.timedelta(days=reminder_days)
                
                # Only schedule if the reminder date is in the future
                if reminder_date > datetime.datetime.now():
                    add_reminder(
                        discord_id, 
                        current_assignment, 
                        due_date.strftime('%Y-%m-%d'), 
                        reminder_date.strftime('%Y-%m-%d')
                    )
            except ValueError:
                print(f"Could not parse date: {due_date_str}")
        
        i += 1