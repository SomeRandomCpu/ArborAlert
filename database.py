import sqlite3
import os
from cryptography.fernet import Fernet

# Get the encryption key from environment variables
cipher_suite = Fernet(os.getenv("KEY"))

# Database initialization
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

# Add reminder_days column if it doesn't exist
def add_reminder_days_column():
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

# User credential functions
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

def save_user_credentials(discord_id, username, password):
    encrypted_password = cipher_suite.encrypt(password.encode())
    conn = sqlite3.connect("arbor_users.db")
    cursor = conn.cursor()
    
    # Check if user already exists
    cursor.execute("SELECT id FROM users WHERE discord_id = ?", (discord_id,))
    user = cursor.fetchone()
    
    if user:
        # Update existing user
        cursor.execute(
            "UPDATE users SET username = ?, password = ? WHERE discord_id = ?",
            (username, encrypted_password, discord_id)
        )
    else:
        # Insert new user
        cursor.execute(
            "INSERT INTO users (discord_id, username, password) VALUES (?, ?, ?)",
            (discord_id, username, encrypted_password)
        )
    
    conn.commit()
    conn.close()
    return True

def delete_user_account(discord_id):
    conn = sqlite3.connect("arbor_users.db")
    cursor = conn.cursor()
    
    # Delete reminders first (foreign key constraint)
    cursor.execute("DELETE FROM reminders WHERE discord_id = ?", (discord_id,))
    
    # Delete user
    cursor.execute("DELETE FROM users WHERE discord_id = ?", (discord_id,))
    
    conn.commit()
    conn.close()
    return True

def user_exists(discord_id):
    conn = sqlite3.connect("arbor_users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE discord_id = ?", (discord_id,))
    user = cursor.fetchone()
    conn.close()
    return user is not None

# Reminder functions
def set_reminder_days(discord_id, days_before):
    conn = sqlite3.connect("arbor_users.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET reminder_days = ? WHERE discord_id = ?",
        (days_before, discord_id)
    )
    conn.commit()
    conn.close()
    return True

def get_reminder_days(discord_id):
    conn = sqlite3.connect("arbor_users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT reminder_days FROM users WHERE discord_id = ?", (discord_id,))
    result = cursor.fetchone()
    conn.close()
    
    reminder_days = 1  # Default
    if result and result[0]:
        reminder_days = result[0]
    
    return reminder_days

def get_user_reminders(discord_id):
    conn = sqlite3.connect("arbor_users.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT assignment_name, due_date, reminder_date FROM reminders WHERE discord_id = ? AND sent = 0 ORDER BY due_date",
        (discord_id,)
    )
    reminders = cursor.fetchall()
    conn.close()
    return reminders

def clear_user_reminders(discord_id):
    conn = sqlite3.connect("arbor_users.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reminders WHERE discord_id = ? AND sent = 0", (discord_id,))
    conn.commit()
    conn.close()

def add_reminder(discord_id, assignment_name, due_date, reminder_date):
    conn = sqlite3.connect("arbor_users.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO reminders (discord_id, assignment_name, due_date, reminder_date, sent) VALUES (?, ?, ?, ?, ?)",
        (discord_id, assignment_name, due_date, reminder_date, 0)
    )
    conn.commit()
    conn.close()

def get_due_reminders(date):
    conn = sqlite3.connect("arbor_users.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT discord_id, assignment_name, due_date FROM reminders WHERE reminder_date = ? AND sent = 0",
        (date,)
    )
    reminders = cursor.fetchall()
    conn.close()
    return reminders

def mark_reminder_sent(discord_id, assignment_name, due_date):
    conn = sqlite3.connect("arbor_users.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE reminders SET sent = 1 WHERE discord_id = ? AND assignment_name = ? AND due_date = ?",
        (discord_id, assignment_name, due_date)
    )
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect("arbor_users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT discord_id FROM users")
    users = cursor.fetchall()
    conn.close()
    return users