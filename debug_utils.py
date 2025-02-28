# Debug utilities for ArborAlert
import sqlite3
import os
import datetime
import traceback
from cryptography.fernet import Fernet
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from time import sleep

class DebugTests:
    def __init__(self, bot, cipher_suite):
        self.bot = bot
        self.cipher_suite = cipher_suite
        self.results = []
        self.success_count = 0
        self.fail_count = 0
    
    def add_result(self, test_name, success, message):
        status = "✅ PASS" if success else "❌ FAIL"
        self.results.append(f"{status} - {test_name}: {message}")
        if success:
            self.success_count += 1
        else:
            self.fail_count += 1
    
    def get_summary(self):
        summary = f"__**Debug Test Results**__\n\n"
        summary += f"Tests passed: {self.success_count}\n"
        summary += f"Tests failed: {self.fail_count}\n\n"
        
        for result in self.results:
            summary += f"{result}\n"
            
        return summary
    
    async def run_all_tests(self, discord_id=None):
        self.results = []
        self.success_count = 0
        self.fail_count = 0
        
        # Run all tests
        self.test_database_connection()
        self.test_env_variables()
        
        if discord_id:
            self.test_user_exists(discord_id)
            self.test_encryption_decryption(discord_id)
            await self.test_reminder_system(discord_id)
        
        return self.get_summary()
    
    def test_database_connection(self):
        try:
            conn = sqlite3.connect("arbor_users.db")
            cursor = conn.cursor()
            
            # Check users table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            users_table_exists = cursor.fetchone() is not None
            
            # Check reminders table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reminders'")
            reminders_table_exists = cursor.fetchone() is not None
            
            conn.close()
            
            if users_table_exists and reminders_table_exists:
                self.add_result("Database Connection", True, "Successfully connected to database and verified tables")
            else:
                missing_tables = []
                if not users_table_exists:
                    missing_tables.append("users")
                if not reminders_table_exists:
                    missing_tables.append("reminders")
                self.add_result("Database Connection", False, f"Missing tables: {', '.join(missing_tables)}")
        except Exception as e:
            self.add_result("Database Connection", False, f"Error: {str(e)}")
    
    def test_env_variables(self):
        required_vars = ["KEY", "arborurl", "Bot-key"]
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if not missing_vars:
            self.add_result("Environment Variables", True, "All required environment variables are set")
        else:
            self.add_result("Environment Variables", False, f"Missing variables: {', '.join(missing_vars)}")
    
    def test_user_exists(self, discord_id):
        try:
            conn = sqlite3.connect("arbor_users.db")
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE discord_id = ?", (str(discord_id),))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                self.add_result("User Exists", True, f"User with Discord ID {discord_id} exists in database")
            else:
                self.add_result("User Exists", False, f"User with Discord ID {discord_id} not found in database")
        except Exception as e:
            self.add_result("User Exists", False, f"Error: {str(e)}")
    
    def test_encryption_decryption(self, discord_id):
        try:
            conn = sqlite3.connect("arbor_users.db")
            cursor = conn.cursor()
            cursor.execute("SELECT username, password FROM users WHERE discord_id = ?", (str(discord_id),))
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                self.add_result("Encryption/Decryption", False, "User not found, cannot test encryption")
                return
            
            username, encrypted_password = result
            
            try:
                # Try to decrypt the password
                decrypted_password = self.cipher_suite.decrypt(encrypted_password).decode()
                
                # Test re-encryption
                re_encrypted = self.cipher_suite.encrypt(decrypted_password.encode())
                re_decrypted = self.cipher_suite.decrypt(re_encrypted).decode()
                
                if decrypted_password == re_decrypted:
                    self.add_result("Encryption/Decryption", True, "Successfully tested encryption and decryption")
                else:
                    self.add_result("Encryption/Decryption", False, "Re-encryption test failed")
            except Exception as e:
                self.add_result("Encryption/Decryption", False, f"Decryption error: {str(e)}")
        except Exception as e:
            self.add_result("Encryption/Decryption", False, f"Database error: {str(e)}")
    
    async def test_reminder_system(self, discord_id):
        try:
            # Check if user has any reminders
            conn = sqlite3.connect("arbor_users.db")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM reminders WHERE discord_id = ?",
                (str(discord_id),)
            )
            reminder_count = cursor.fetchone()[0]
            
            if reminder_count > 0:
                self.add_result("Reminder System", True, f"User has {reminder_count} reminders in the database")
            else:
                # Create a test reminder for today to verify the system
                today = datetime.datetime.now().strftime('%Y-%m-%d')
                test_assignment = "[TEST] Debug Assignment"
                
                cursor.execute(
                    "INSERT INTO reminders (discord_id, assignment_name, due_date, reminder_date, sent) VALUES (?, ?, ?, ?, ?)",
                    (str(discord_id), test_assignment, today, today, 0)
                )
                conn.commit()
                
                # Verify the reminder was added
                cursor.execute(
                    "SELECT id FROM reminders WHERE discord_id = ? AND assignment_name = ?",
                    (str(discord_id), test_assignment)
                )
                test_reminder = cursor.fetchone()
                
                if test_reminder:
                    self.add_result("Reminder System", True, "Successfully created a test reminder")
                    
                    # Clean up the test reminder
                    cursor.execute(
                        "DELETE FROM reminders WHERE discord_id = ? AND assignment_name = ?",
                        (str(discord_id), test_assignment)
                    )
                    conn.commit()
                else:
                    self.add_result("Reminder System", False, "Failed to create test reminder")
            
            conn.close()
        except Exception as e:
            self.add_result("Reminder System", False, f"Error: {str(e)}")
    
    def test_arbor_connection(self, discord_id):
        try:
            # Get user credentials
            conn = sqlite3.connect("arbor_users.db")
            cursor = conn.cursor()
            cursor.execute("SELECT username, password FROM users WHERE discord_id = ?", (discord_id,))
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                self.add_result("Arbor Connection", False, "User not found, cannot test Arbor connection")
                return
            
            username, encrypted_password = result
            password = self.cipher_suite.decrypt(encrypted_password).decode()
            
            # Use headless browser for testing
            options = Options()
            options.headless = True
            driver = webdriver.Firefox(options=options)
            
            try:
                driver.get(os.getenv("arborurl"))
                
                # Check if login page loaded
                try:
                    email_input = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Email address']"))
                    )
                    self.add_result("Arbor Connection", True, "Successfully connected to Arbor login page")
                    
                    # Don't actually log in during debug test
                    # This just verifies we can reach the login page
                except Exception as e:
                    self.add_result("Arbor Connection", False, f"Could not find login form: {str(e)}")
            except Exception as e:
                self.add_result("Arbor Connection", False, f"Failed to connect to Arbor: {str(e)}")
            finally:
                driver.quit()
        except Exception as e:
            self.add_result("Arbor Connection", False, f"Error: {str(e)}")

# Function to get detailed system information
def get_system_info():
    info = []
    
    # Python version
    import sys
    info.append(f"Python version: {sys.version}")
    
    # Selenium version
    import selenium
    info.append(f"Selenium version: {selenium.__version__}")
    
    # Discord.py version
    import discord
    info.append(f"Discord.py version: {discord.__version__}")
    
    # Check Firefox installation
    try:
        options = Options()
        options.headless = True
        driver = webdriver.Firefox(options=options)
        driver.quit()
        info.append("Firefox webdriver: Available")
    except Exception as e:
        info.append(f"Firefox webdriver: Not available - {str(e)}")
    
    # Database info
    try:
        conn = sqlite3.connect("arbor_users.db")
        cursor = conn.cursor()
        
        # Get user count
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        info.append(f"Database users: {user_count}")
        
        # Get reminder count
        cursor.execute("SELECT COUNT(*) FROM reminders")
        reminder_count = cursor.fetchone()[0]
        info.append(f"Database reminders: {reminder_count}")
        
        conn.close()
    except Exception as e:
        info.append(f"Database info: Error - {str(e)}")
    
    return "\n".join(info)