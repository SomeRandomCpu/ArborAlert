# Debug utilities for ArborAlert
import sqlite3
import os
import datetime
import traceback
import asyncio
import re
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
        self.total_tests = 0
        self.current_test = 0
        self.interaction = None
        self.progress_message = None
    
    def add_result(self, test_name, success, message):
        status = "✅ PASS" if success else "❌ FAIL"
        self.results.append(f"{status} - {test_name}: {message}")
        if success:
            self.success_count += 1
        else:
            self.fail_count += 1
        
        # Update progress
        self.current_test += 1
        asyncio.create_task(self.update_progress())
    
    async def update_progress(self):
        if self.interaction and self.progress_message:
            # Cap progress at 100%
            progress_percent = min((self.current_test / self.total_tests * 100), 100) if self.total_tests > 0 else 0
            bar_length = 20
            filled_length = int(bar_length * progress_percent / 100)
            progress_bar = "🟩" * filled_length + "⬜" * (bar_length - filled_length)
            
            status_text = f"🔄 **Running Diagnostics:** {self.current_test}/{self.total_tests} tests completed\n"
            status_text += f"┌─────────────────────────────────────┐\n"
            status_text += f"│ 🟢 **Passed:** {self.success_count} | 🔴 **Failed:** {self.fail_count} │\n"
            # Ensure consistent spacing for percentage display
            progress_display = f"{progress_percent:.1f}%"
            padding = ' ' * (14 - len(progress_display))
            status_text += f"│ 📊 **Progress:** {progress_display}{padding}│\n"
            status_text += f"│ {progress_bar} │\n"
            status_text += f"└─────────────────────────────────────┘\n"
            
            try:
                await self.progress_message.edit(content=status_text)
            except:
                pass  # Ignore errors if message can't be edited
    
    def get_summary(self):
        # Calculate success percentage
        total_tests = self.success_count + self.fail_count
        success_percentage = (self.success_count / total_tests * 100) if total_tests > 0 else 0
        
        # Create a visual progress bar
        bar_length = 20
        filled_length = int(bar_length * success_percentage / 100)
        progress_bar = "🟩" * filled_length + "⬜" * (bar_length - filled_length)
        
        # Create a header with emoji
        summary = f"🔍 **ARBORALERT DIAGNOSTIC REPORT** 🔍\n\n"
        
        # Add status overview with emojis and formatting
        summary += f"**Status Overview:**\n"
        summary += f"┌─────────────────────────────────────┐\n"
        summary += f"│ 🟢 **Tests Passed:** {self.success_count} | 🔴 **Tests Failed:** {self.fail_count} │\n"
        summary += f"│ 📊 **Success Rate:** {success_percentage:.1f}%              │\n"
        summary += f"│ {progress_bar} │\n"
        summary += f"└─────────────────────────────────────┘\n\n"
        
        # Group results by category
        database_tests = []
        connection_tests = []
        system_tests = []
        user_tests = []
        
        for result in self.results:
            if "Database" in result:
                database_tests.append(result)
            elif "Connection" in result or "Selenium" in result:
                connection_tests.append(result)
            elif "File" in result or "Environment" in result:
                system_tests.append(result)
            else:
                user_tests.append(result)
        
        # Add results by category with emoji headers
        if system_tests:
            summary += f"⚙️ **SYSTEM TESTS**\n"
            summary += "```\n"
            for result in system_tests:
                summary += f"{result}\n"
            summary += "```\n\n"
            
        if database_tests:
            summary += f"💾 **DATABASE TESTS**\n"
            summary += "```\n"
            for result in database_tests:
                summary += f"{result}\n"
            summary += "```\n\n"
            
        if connection_tests:
            summary += f"🌐 **CONNECTION TESTS**\n"
            summary += "```\n"
            for result in connection_tests:
                summary += f"{result}\n"
            summary += "```\n\n"
            
        if user_tests:
            summary += f"👤 **USER TESTS**\n"
            summary += "```\n"
            for result in user_tests:
                summary += f"{result}\n"
            summary += "```\n\n"
        
        return summary
    
    async def test_ai_system(self, discord_id=None):
        try:
            # Check if ai_handler.py exists and is readable
            if not os.path.exists("ai_handler.py"):
                self.add_result("AI System", False, "ai_handler.py file not found")
                return
                
            if not os.access("ai_handler.py", os.R_OK):
                self.add_result("AI System", False, "Cannot read ai_handler.py file")
                return
                
            # Check if the required functions exist in the module
            import importlib
            import inspect
            
            try:
                # Try to import the module
                ai_module = importlib.import_module("ai_handler")
                
                # Check for process_message function
                if not hasattr(ai_module, "process_message") or not inspect.iscoroutinefunction(ai_module.process_message):
                    self.add_result("AI System", False, "process_message function not found or not async")
                    return
                    
                # Check for BaseMockInteraction class
                if not hasattr(ai_module, "BaseMockInteraction"):
                    self.add_result("AI System", False, "BaseMockInteraction class not found")
                    return
                    
                # Check for handler functions
                required_handlers = ["handle_fetch_request", "handle_set_reminder", "handle_view_reminders", 
                                    "handle_setup", "handle_change_credentials", "handle_delete_account", 
                                    "handle_debug"]
                                    
                missing_handlers = []
                for handler in required_handlers:
                    if not hasattr(ai_module, handler) or not inspect.iscoroutinefunction(getattr(ai_module, handler)):
                        missing_handlers.append(handler)
                
                if missing_handlers:
                    self.add_result("AI System", False, f"Missing handler functions: {', '.join(missing_handlers)}")
                    return
                    
                # Check for PATTERNS dictionary
                if not hasattr(ai_module, "PATTERNS") or not isinstance(ai_module.PATTERNS, dict):
                    self.add_result("AI System", False, "PATTERNS dictionary not found")
                    return
                    
                # All checks passed
                self.add_result("AI System", True, "AI system components verified successfully")
                
            except ImportError as e:
                self.add_result("AI System", False, f"Error importing ai_handler module: {str(e)}")
            except Exception as e:
                self.add_result("AI System", False, f"Error checking AI system: {str(e)}")
                
        except Exception as e:
            self.add_result("AI System", False, f"Error: {str(e)}")
            
    async def run_all_tests(self, interaction=None, discord_id=None, full_test=False):
        self.interaction = interaction
        self.results = []
        self.success_count = 0
        self.fail_count = 0
        self.current_test = 0
        
        # Update total tests to include AI tests
        self.total_tests = 4  # Base tests (database_connection, env_variables, file_permissions, ai_system)
        if discord_id:
            self.total_tests += 3  # User tests (user_exists, encryption_decryption, reminder_system)
            if full_test:
                self.total_tests += 6  # Full tests (arbor_connection, selenium_setup(2), browser_functionality, database_integrity(3))
        
        # Create initial progress message
        if self.interaction:
            try:
                self.progress_message = await self.interaction.followup.send(
                    "🔄 **Starting Diagnostics...**\n" +
                    "┌─────────────────────────────────────┐\n" +
                    "│ 🟢 **Passed:** 0 | 🔴 **Failed:** 0 │\n" +
                    "│ 📊 **Progress:** 0.0%              │\n" +
                    "│ ⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ │\n" +
                    "└─────────────────────────────────────┘",
                    ephemeral=True
                )
            except:
                self.progress_message = None
        
        # Run all tests with a small delay between each test to allow progress updates
        self.test_database_connection()
        await asyncio.sleep(1)  # Add delay for UI update
        
        self.test_env_variables()
        await asyncio.sleep(1)  # Add delay for UI update
        
        self.test_file_permissions()
        await asyncio.sleep(1)  # Add delay for UI update
        
        # Add AI system test
        await self.test_ai_system(discord_id)
        await asyncio.sleep(1)  # Add delay for UI update
        
        if discord_id:
            self.test_user_exists(discord_id)
            await asyncio.sleep(1)  # Add delay for UI update
            
            self.test_encryption_decryption(discord_id)
            await asyncio.sleep(1)  # Add delay for UI update
            
            await self.test_reminder_system(discord_id)
            await asyncio.sleep(1)  # Add delay for UI update
            
            if full_test:
                self.test_arbor_connection(discord_id)
                await asyncio.sleep(1)  # Add delay for UI update
                
                self.test_selenium_setup()
                await asyncio.sleep(1)  # Add delay for UI update
                
                self.test_database_integrity()
                await asyncio.sleep(1)  # Add delay for UI update
        
        # Get system information
        system_info = get_system_info()
        
        # Combine system info with test results
        full_report = f"🔍 **ARBORALERT DIAGNOSTIC REPORT** 🔍\n\n"
        
        # Add status overview
        total_tests = self.success_count + self.fail_count
        success_percentage = (self.success_count / total_tests * 100) if total_tests > 0 else 0
        bar_length = 20
        filled_length = int(bar_length * success_percentage / 100)
        progress_bar = "🟩" * filled_length + "⬜" * (bar_length - filled_length)
        
        full_report += f"**Status Overview:**\n"
        full_report += f"┌─────────────────────────────────────┐\n"
        full_report += f"│ 🟢 **Tests Passed:** {self.success_count} | 🔴 **Tests Failed:** {self.fail_count} │\n"
        full_report += f"│ 📊 **Success Rate:** {success_percentage:.1f}%              │\n"
        full_report += f"│ {progress_bar} │\n"
        full_report += f"└─────────────────────────────────────┘\n\n"
        
        # Add system information section
        full_report += f"📊 **SYSTEM INFORMATION**\n"
        full_report += "```\n"
        full_report += system_info
        full_report += "\n```\n\n"
        
        # Add test results by category
        database_tests = []
        connection_tests = []
        system_tests = []
        user_tests = []
        
        for result in self.results:
            if "Database" in result:
                database_tests.append(result)
            elif "Connection" in result or "Selenium" in result:
                connection_tests.append(result)
            elif "File" in result or "Environment" in result:
                system_tests.append(result)
            else:
                user_tests.append(result)
        
        if system_tests:
            full_report += f"⚙️ **SYSTEM TESTS**\n"
            full_report += "```\n"
            for result in system_tests:
                full_report += f"{result}\n"
            full_report += "```\n\n"
            
        if database_tests:
            full_report += f"💾 **DATABASE TESTS**\n"
            full_report += "```\n"
            for result in database_tests:
                full_report += f"{result}\n"
            full_report += "```\n\n"
            
        if connection_tests:
            full_report += f"🌐 **CONNECTION TESTS**\n"
            full_report += "```\n"
            for result in connection_tests:
                full_report += f"{result}\n"
            full_report += "```\n\n"
            
        if user_tests:
            full_report += f"👤 **USER TESTS**\n"
            full_report += "```\n"
            for result in user_tests:
                full_report += f"{result}\n"
            full_report += "```\n\n"
        
        return full_report
    
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

    def test_file_permissions(self):
        try:
            # Check if key files are readable
            files_to_check = ["main.py", "database.py", "reminder_system.py", "arbor_processor.py", "bot_commands.py"]
            missing_files = []
            
            for file in files_to_check:
                if not os.path.exists(file):
                    missing_files.append(file)
                elif not os.access(file, os.R_OK):
                    self.add_result("File Permissions", False, f"Cannot read {file}")
                    return
            
            if missing_files:
                self.add_result("File Permissions", False, f"Missing files: {', '.join(missing_files)}")
            else:
                self.add_result("File Permissions", True, "All required files are present and readable")
        except Exception as e:
            self.add_result("File Permissions", False, f"Error checking file permissions: {str(e)}")
    
    def test_selenium_setup(self):
        try:
            # Test if Selenium and Firefox are properly configured
            options = Options()
            options.headless = True
            
            # Set a timeout for driver creation
            driver = None
            try:
                driver = webdriver.Firefox(options=options)
                self.add_result("Selenium Setup", True, "Firefox webdriver initialized successfully")
                
                # Test basic browser functionality
                driver.get("about:blank")
                if driver.title is not None:
                    self.add_result("Browser Functionality", True, "Browser can load pages")
                else:
                    self.add_result("Browser Functionality", False, "Browser failed to load test page")
            except Exception as e:
                self.add_result("Selenium Setup", False, f"Failed to initialize Firefox webdriver: {str(e)}")
            finally:
                if driver:
                    driver.quit()
        except Exception as e:
            self.add_result("Selenium Setup", False, f"Error in Selenium test: {str(e)}")
    
    def test_database_integrity(self):
        try:
            conn = sqlite3.connect("arbor_users.db")
            cursor = conn.cursor()
            
            # Check users table structure
            cursor.execute("PRAGMA table_info(users)")
            columns = {column[1] for column in cursor.fetchall()}
            required_columns = {"id", "discord_id", "username", "password", "reminder_days"}
            
            if required_columns.issubset(columns):
                self.add_result("Users Table Structure", True, "Users table has all required columns")
            else:
                missing = required_columns - columns
                self.add_result("Users Table Structure", False, f"Missing columns: {', '.join(missing)}")
            
            # Check reminders table structure
            cursor.execute("PRAGMA table_info(reminders)")
            columns = {column[1] for column in cursor.fetchall()}
            required_columns = {"id", "discord_id", "assignment_name", "due_date", "reminder_date", "sent"}
            
            if required_columns.issubset(columns):
                self.add_result("Reminders Table Structure", True, "Reminders table has all required columns")
            else:
                missing = required_columns - columns
                self.add_result("Reminders Table Structure", False, f"Missing columns: {', '.join(missing)}")
            
            # Check for orphaned reminders (reminders without a corresponding user)
            cursor.execute("""
                SELECT COUNT(*) FROM reminders r 
                WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.discord_id = r.discord_id)
            """)
            orphaned_count = cursor.fetchone()[0]
            
            if orphaned_count == 0:
                self.add_result("Database Integrity", True, "No orphaned reminders found")
            else:
                self.add_result("Database Integrity", False, f"Found {orphaned_count} orphaned reminders")
                
            conn.close()
        except Exception as e:
            self.add_result("Database Integrity", False, f"Error checking database integrity: {str(e)}")

# Function to get detailed system information
def get_system_info():
    # Use a dictionary to organize info by category
    info_dict = {
        "Environment": [],
        "Dependencies": [],
        "Database": []
    }
    
    # Environment info
    import platform
    import sys
    info_dict["Environment"].append(f"🖥️  OS: {platform.system()} {platform.release()}")
    info_dict["Environment"].append(f"🐍 Python: {sys.version.split()[0]}")
    
    # Dependencies versions
    import selenium
    import discord
    info_dict["Dependencies"].append(f"🤖 Discord.py: v{discord.__version__}")
    info_dict["Dependencies"].append(f"🌐 Selenium: v{selenium.__version__}")
    
    # Check Firefox installation
    try:
        options = Options()
        options.headless = True
        driver = webdriver.Firefox(options=options)
        driver.quit()
        info_dict["Dependencies"].append("🦊 Firefox: ✅ Available")
    except Exception as e:
        info_dict["Dependencies"].append(f"🦊 Firefox: ❌ Not available")
    
    # Database info
    try:
        conn = sqlite3.connect("arbor_users.db")
        cursor = conn.cursor()
        
        # Get user count
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        info_dict["Database"].append(f"👥 Users: {user_count}")
        
        # Get reminder count
        cursor.execute("SELECT COUNT(*) FROM reminders")
        reminder_count = cursor.fetchone()[0]
        info_dict["Database"].append(f"📝 Total reminders: {reminder_count}")
        
        # Get active reminders count
        cursor.execute("SELECT COUNT(*) FROM reminders WHERE sent = 0")
        active_reminders = cursor.fetchone()[0]
        info_dict["Database"].append(f"⏰ Active reminders: {active_reminders}")
        
        conn.close()
    except Exception as e:
        info_dict["Database"].append(f"💾 Database: ❌ Error connecting")
    
    # Format the output with sections
    formatted_info = []
    
    for section, items in info_dict.items():
        if items:
            formatted_info.append(f"== {section} ===")
            formatted_info.extend(items)
            formatted_info.append("")
    
    return "\n".join(formatted_info).strip()