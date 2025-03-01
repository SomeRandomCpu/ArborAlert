import discord
from discord.ext import commands
import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import traceback

# Import our modules
from database import init_db, add_reminder_days_column
from reminder_system import init_scheduler, check_reminders
from bot_commands import (
    setup_command, fetch_command, set_reminder_command, view_reminders_command,
    delete_account_command, change_credentials_command, debug_command
)
from embed_utils import create_basic_embed, create_error_embed
from ai_handler import process_message

# Load environment variables
load_dotenv()

# Initialize encryption
cipher_suite = Fernet(os.getenv("KEY"))

# Initialize database
init_db()
add_reminder_days_column()

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
        
        # Initialize the scheduler
        init_scheduler()
        
        # Start the background task for checking reminders
        bot.loop.create_task(check_reminders(bot))
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.event
async def on_message(message):
    # Process commands first
    await bot.process_commands(message)
    
    # Then process natural language
    await process_message(message, bot)

# Register commands
@bot.tree.command(name="setup")
async def setup(interaction: discord.Interaction):
    """Set up your Arbor credentials"""
    await setup_command(bot, interaction)

@bot.tree.command(name="fetch")
async def fetch(interaction: discord.Interaction):
    """Fetch your homework assignments from Arbor"""
    await fetch_command(interaction)

@bot.tree.command(name="set_reminder")
async def set_reminder(interaction: discord.Interaction, days_before: int = 1):
    """Set how many days before the due date you want to be reminded"""
    await set_reminder_command(interaction, days_before)

@bot.tree.command(name="view_reminders")
async def view_reminders(interaction: discord.Interaction):
    """View your upcoming assignment reminders"""
    await view_reminders_command(interaction)

@bot.tree.command(name="delete_account")
async def delete_account(interaction: discord.Interaction):
    """Delete your account and all associated data from ArborAlert"""
    await delete_account_command(bot, interaction)

@bot.tree.command(name="change_credentials")
async def change_credentials(interaction: discord.Interaction):
    """Update your Arbor login credentials"""
    await change_credentials_command(bot, interaction)

@bot.tree.command(name="debug")
async def debug(interaction: discord.Interaction, full_test: bool = False, test_error: str = None):
    """Run diagnostic tests on the bot to identify issues"""
    await debug_command(bot, interaction, full_test, cipher_suite, test_error)

# Run the bot
if __name__ == "__main__":
    try:
        bot.run(os.getenv("Bot-key"))
    except Exception as e:
        print(f"Error starting bot: {e}")
        print(traceback.format_exc())