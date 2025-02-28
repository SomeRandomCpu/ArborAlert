from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import discord
from discord.ext import commands
import os
import sqlite3
from cryptography.fernet import Fernet
from dotenv import load_dotenv, dotenv_values
import schedule
import time
import datetime
import re
import asyncio
from threading import Thread
load_dotenv()

cipher_suite = Fernet(os.getenv("KEY"))

# Database setup
def init_db():
    conn = None
    try:
        conn = sqlite3.connect("arbor_users.db")
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id TEXT NOT NULL,
                username TEXT NOT NULL,
                password TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id TEXT NOT NULL,
                assignment_name TEXT NOT NULL,
                due_date TEXT NOT NULL,
                reminder_date TEXT NOT NULL,
                sent INTEGER DEFAULT 0
            )
            """
        )
        conn.commit()
    except Exception as e:
        print(f"Error initializing database: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

init_db()

# Discord Bot Setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    print("Bot is online and waiting for commands.")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
        
        # Start the scheduler in a separate thread
        scheduler_thread = Thread(target=run_scheduler)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        
        # Start the background task for checking reminders
        bot.loop.create_task(check_reminders())
    except Exception as e:
        print(f"Failed to sync commands: {e}")

# Setup command
@bot.tree.command(name="setup")
async def setup(interaction: discord.Interaction):
    await interaction.response.send_message("Please enter your Arbor email:")

    def check_username(m):
        return m.author == interaction.user and isinstance(m.channel, discord.DMChannel)

    try:
        username_msg = await bot.wait_for("message", check=check_username, timeout=60)
        username = username_msg.content

        await interaction.user.send("Now enter your Arbor password:")

        def check_password(m):
            return m.author == interaction.user and isinstance(m.channel, discord.DMChannel)

        password_msg = await bot.wait_for("message", check=check_password, timeout=60)
        password = password_msg.content

        # Encrypt the password
        encrypted_password = cipher_suite.encrypt(password.encode())

        # Save to database
        conn = sqlite3.connect("arbor_users.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (discord_id, username, password) VALUES (?, ?, ?)",
            (str(interaction.user.id), username, encrypted_password)
        )
        conn.commit()
        conn.close()

        await interaction.user.send("# Welcome to ArborAlert, a bot that notifies you to do your homework\n"
        "You've successfully set up the bot! 🎉\n"
        "Please delete the messages where you sent your username and password for security. The bot fetches your homework automatically once a day, but you can run it manually by using the /fetch command.\n"
        "Send a message in the arboralert-support channel if you have any issues!")
    except Exception as e:
        await interaction.user.send(f"An error occurred: {e}")

# Function to fetch credentials from the database
def get_credentials(discord_id):
    conn = sqlite3.connect("arbor_users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT username, password FROM users WHERE discord_id = ?", (discord_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        username, encrypted_password = result
        password = cipher_suite.decrypt(encrypted_password).decode()
        return username, password
    return None, None

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

# Process document function moved outside for better organization
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


# Fetch command
@bot.tree.command(name="fetch")
async def fetch(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
        process_arbor_data(interaction.user.id)
        
        # Read the processed text and send it to the user
        try:
            with open("arbor_processed_text.txt", "r", encoding="utf-8") as file:
                text = file.read()

            # Send the processed text to the user's DM
            await interaction.user.send(f"{text}")

            # Follow up on the original interaction
            await interaction.followup.send("Success! Say thanks to Duplicake_ (don't actually though, I don't want loads of DMs)", ephemeral=True)
        except FileNotFoundError:
            await interaction.followup.send("Error: The processed text file was not found.", ephemeral=True)
            return
    except Exception as e:
        await interaction.followup.send(f"Critical error occurred: {e}", ephemeral=True)
        return
    finally:
        # Only delete files if they exist
        if os.path.exists("arbor_text.txt"):
            os.remove("arbor_text.txt")
        if os.path.exists("arbor_processed_text.txt"):
            os.remove("arbor_processed_text.txt")

# Set reminder command
@bot.tree.command(name="set_reminder")
async def set_reminder(interaction: discord.Interaction, days_before: int = 1):
    """Set how many days before the due date you want to be reminded"""
    try:
        conn = sqlite3.connect("arbor_users.db")
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET reminder_days = ? WHERE discord_id = ?",
            (days_before, str(interaction.user.id))
        )
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"You will now be reminded {days_before} day(s) before assignments are due.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

# View reminders command
@bot.tree.command(name="view_reminders")
async def view_reminders(interaction: discord.Interaction):
    """View your upcoming assignment reminders"""
    try:
        conn = sqlite3.connect("arbor_users.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT assignment_name, due_date, reminder_date FROM reminders WHERE discord_id = ? AND sent = 0 ORDER BY due_date",
            (str(interaction.user.id),)
        )
        reminders = cursor.fetchall()
        conn.close()
        
        if not reminders:
            await interaction.response.send_message("You don't have any upcoming reminders.", ephemeral=True)
            return
            
        reminder_text = "__**Your upcoming assignment reminders:**__\n\n"
        for assignment, due_date, reminder_date in reminders:
            reminder_text += f"**{assignment}**\nDue: {due_date}\nReminder scheduled: {reminder_date}\n\n"
            
        await interaction.response.send_message(reminder_text, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

# Parse assignments and schedule reminders
def parse_assignments_and_schedule(content, discord_id):
    # Get user's reminder preference (default to 1 day before)
    conn = None
    try:
        conn = sqlite3.connect("arbor_users.db")
        cursor = conn.cursor()
        cursor.execute("SELECT reminder_days FROM users WHERE discord_id = ?", (discord_id,))
        result = cursor.fetchone()
        reminder_days = 1  # Default
        if result and result[0]:
            reminder_days = result[0]
        
        # Clear existing reminders for this user
        cursor.execute("DELETE FROM reminders WHERE discord_id = ? AND sent = 0", (discord_id,))
        conn.commit()
    
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
                    cursor.execute(
                        "INSERT INTO reminders (discord_id, assignment_name, due_date, reminder_date) VALUES (?, ?, ?, ?)",
                        (discord_id, current_assignment, due_date.strftime('%Y-%m-%d'), reminder_date.strftime('%Y-%m-%d'))
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
                        cursor.execute(
                            "INSERT INTO reminders (discord_id, assignment_name, due_date, reminder_date) VALUES (?, ?, ?, ?)",
                            (discord_id, current_assignment, due_date_str, reminder_date.strftime('%Y-%m-%d'))
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
                    cursor.execute(
                        "INSERT INTO reminders (discord_id, assignment_name, due_date, reminder_date) VALUES (?, ?, ?, ?)",
                        (discord_id, current_assignment, due_date.strftime('%Y-%m-%d'), reminder_date.strftime('%Y-%m-%d'))
                    )
            except ValueError:
                print(f"Could not parse date: {due_date_str}")
        
        i += 1
    
        conn.commit()
    except Exception as e:
        print(f"Error in parse_assignments_and_schedule: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

# Function to run the scheduler
def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

# Schedule daily fetch for all users
def schedule_daily_fetch():
    conn = sqlite3.connect("arbor_users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT discord_id FROM users")
    users = cursor.fetchall()
    conn.close()
    
    for user in users:
        discord_id = user[0]
        try:
            process_arbor_data(discord_id)
        except Exception as e:
            print(f"Error fetching data for user {discord_id}: {e}")

# Schedule the daily fetch at 7 AM
schedule.every().day.at("07:00").do(schedule_daily_fetch)

# Background task to check for reminders
async def check_reminders():
    while True:
        conn = None
        try:
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            
            conn = sqlite3.connect("arbor_users.db")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT discord_id, assignment_name, due_date FROM reminders WHERE reminder_date = ? AND sent = 0",
                (today,)
            )
            reminders = cursor.fetchall()
            
            for discord_id, assignment, due_date in reminders:
                try:
                    user = await bot.fetch_user(int(discord_id))
                    await user.send(f"**REMINDER:** Your assignment **{assignment}** is due on {due_date}!")
                    
                    # Mark reminder as sent
                    cursor.execute(
                        "UPDATE reminders SET sent = 1 WHERE discord_id = ? AND assignment_name = ? AND due_date = ?",
                        (discord_id, assignment, due_date)
                    )
                except Exception as e:
                    print(f"Error sending reminder to user {discord_id}: {e}")
            
            conn.commit()
        except Exception as e:
            print(f"Error checking reminders: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()
        
        # Check every hour
        await asyncio.sleep(3600)

# Add reminder_days column to users table if it doesn't exist
conn = sqlite3.connect("arbor_users.db")
cursor = conn.cursor()
try:
    # Check if the column exists first
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    if "reminder_days" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN reminder_days INTEGER DEFAULT 1")
        conn.commit()
        print("Added reminder_days column to users table")
except Exception as e:
    print(f"Error adding reminder_days column: {e}")
finally:
    conn.close()

# Delete account command
@bot.tree.command(name="delete_account")
async def delete_account(interaction: discord.Interaction):
    """Delete your account and all associated data from ArborAlert"""
    try:
        # Check if user exists in database
        conn = sqlite3.connect("arbor_users.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE discord_id = ?", (str(interaction.user.id),))
        user = cursor.fetchone()
        
        if not user:
            await interaction.response.send_message("You don't have an account to delete.", ephemeral=True)
            conn.close()
            return
        
        # Confirm deletion with user
        await interaction.response.send_message(
            "⚠️ **WARNING: Account Deletion** ⚠️\n\n"
            "This will permanently delete your account and all your reminders from ArborAlert.\n"
            "Your data cannot be recovered after deletion.\n\n"
            "Are you sure you want to proceed? Reply with 'yes' to confirm or 'no' to cancel.",
            ephemeral=True
        )
        
        def check_confirmation(m):
            return m.author == interaction.user and isinstance(m.channel, discord.DMChannel) and \
                   m.content.lower() in ['yes', 'no']
        
        try:
            confirmation = await bot.wait_for("message", check=check_confirmation, timeout=60)
            
            if confirmation.content.lower() == 'no':
                await interaction.user.send("Account deletion cancelled.")
                conn.close()
                return
            
            # Delete user data
            cursor.execute("DELETE FROM reminders WHERE discord_id = ?", (str(interaction.user.id),))
            cursor.execute("DELETE FROM users WHERE discord_id = ?", (str(interaction.user.id),))
            conn.commit()
            conn.close()
            
            await interaction.user.send("Your account and all associated data have been successfully deleted from ArborAlert.")
            
        except asyncio.TimeoutError:
            await interaction.user.send("Account deletion timed out. No changes were made to your account.")
            conn.close()
            
    except Exception as e:
        await interaction.user.send(f"An error occurred while trying to delete your account: {e}")
        if 'conn' in locals():
            conn.close()

# Change credentials command
@bot.tree.command(name="change_credentials")
async def change_credentials(interaction: discord.Interaction):
    """Update your Arbor login credentials"""
    try:
        # Check if user exists in database
        conn = sqlite3.connect("arbor_users.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE discord_id = ?", (str(interaction.user.id),))
        user = cursor.fetchone()
        
        if not user:
            await interaction.response.send_message("You need to set up an account first using the /setup command.", ephemeral=True)
            conn.close()
            return
        
        await interaction.response.send_message("I'll help you update your Arbor credentials. Please check your DMs.", ephemeral=True)
        await interaction.user.send("Please enter your new Arbor email:")
        
        def check_username(m):
            return m.author == interaction.user and isinstance(m.channel, discord.DMChannel)
        
        try:
            username_msg = await bot.wait_for("message", check=check_username, timeout=60)
            username = username_msg.content
            
            await interaction.user.send("Now enter your new Arbor password:")
            
            def check_password(m):
                return m.author == interaction.user and isinstance(m.channel, discord.DMChannel)
            
            password_msg = await bot.wait_for("message", check=check_password, timeout=60)
            password = password_msg.content
            
            # Encrypt the password
            encrypted_password = cipher_suite.encrypt(password.encode())
            
            # Update database
            cursor.execute(
                "UPDATE users SET username = ?, password = ? WHERE discord_id = ?",
                (username, encrypted_password, str(interaction.user.id))
            )
            conn.commit()
            conn.close()
            
            await interaction.user.send("Your Arbor credentials have been successfully updated! 🎉\n"
                                      "Please delete the messages where you sent your username and password for security.")
            
        except asyncio.TimeoutError:
            await interaction.user.send("The credential update process timed out. Please try again later.")
            conn.close()
            
    except Exception as e:
        await interaction.user.send(f"An error occurred while updating your credentials: {e}")
        if 'conn' in locals():
            conn.close()

bot.run(os.getenv("Bot-key"))