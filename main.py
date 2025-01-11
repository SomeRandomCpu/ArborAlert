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
load_dotenv()

cipher_suite = Fernet(os.getenv("KEY"))

# Database setup
def init_db():
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
    conn.commit()
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
    finally:
        driver.quit()

    def process_document(file_path, output_path):
        with open(file_path, "r") as file:
            content = file.read()

        start_index = content.find("Overdue Assignments")
        end_index = content.find("Submitted Assignments")
        if start_index == -1 or end_index == -1:
            print("Key phrases not found in the document.")
            return

        content = content.replace("Overdue Assignments", "Overdue Assignments:")
        content = content.replace("Assignments that are due", "Assignments that are due:")
        start_index = content.find("Overdue Assignments:")
        processed_content = content[start_index + len("Overdue Assignments:"):end_index].strip()
        processed_content = processed_content.replace("Assignments that are due:", "", 1).strip()

        with open(output_path, "w") as file:
            file.write(processed_content)

        print(f"Processed text saved to {output_path}")

    process_document("arbor_text.txt", "arbor_processed_text.txt")


# Fetch command
@bot.tree.command(name="fetch")
async def fetch(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
        process_arbor_data(interaction.user.id)
        # Read the processed text and send it to the user
        with open("arbor_processed_text.txt", "r") as file:
            text = file.read()

        # Send the processed text to the user's DM
        await interaction.user.send(f"{text}")

        # Follow up on the original interaction
        await interaction.followup.send("Success! Say thanks to Duplicake_ (don't actually though, I don't want loads of DMs)", ephemeral=True)
    except FileNotFoundError:
        await interaction.followup.send("Error: The processed text file was not found.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Critical error occurred: {e}", ephemeral=True)
    os.remove("arbor_text.txt")
    os.remove("arbor_processed_text.txt")

bot.run(os.getenv("Bot-key"))