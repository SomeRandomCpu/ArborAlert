import discord
import asyncio
import os
import traceback
from database import save_user_credentials, get_user_reminders, set_reminder_days, delete_user_account, user_exists
from arbor_processor import process_arbor_data
from debug_utils import DebugTests, get_system_info

# Setup command
async def setup_command(bot, interaction):
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

        # Save credentials
        save_user_credentials(str(interaction.user.id), username, password)

        await interaction.user.send("# Welcome to ArborAlert, a bot that notifies you to do your homework\n"
        "You've successfully set up the bot! 🎉\n"
        "Please delete the messages where you sent your username and password for security. The bot fetches your homework automatically once a day, but you can run it manually by using the /fetch command.\n"
        "Send a message in the arboralert-support channel if you have any issues!")
    except Exception as e:
        await interaction.user.send(f"An error occurred: {e}")

# Fetch command
async def fetch_command(interaction):
    try:
        await interaction.response.defer()
        process_arbor_data(str(interaction.user.id))
        
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
async def set_reminder_command(interaction, days_before):
    """Set how many days before the due date you want to be reminded"""
    try:
        set_reminder_days(str(interaction.user.id), days_before)
        await interaction.response.send_message(f"You will now be reminded {days_before} day(s) before assignments are due.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

# View reminders command
async def view_reminders_command(interaction):
    """View your upcoming assignment reminders"""
    try:
        reminders = get_user_reminders(str(interaction.user.id))
        
        if not reminders:
            await interaction.response.send_message("You don't have any upcoming reminders.", ephemeral=True)
            return
            
        reminder_text = "__**Your upcoming assignment reminders:**__\n\n"
        for assignment, due_date, reminder_date in reminders:
            reminder_text += f"**{assignment}**\nDue: {due_date}\nReminder scheduled: {reminder_date}\n\n"
            
        await interaction.response.send_message(reminder_text, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

# Delete account command
async def delete_account_command(bot, interaction):
    """Delete your account and all associated data from ArborAlert"""
    try:
        # Check if user exists in database
        if not user_exists(str(interaction.user.id)):
            await interaction.response.send_message("You don't have an account to delete.", ephemeral=True)
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
                return
            
            # Delete user data
            delete_user_account(str(interaction.user.id))
            
            await interaction.user.send("Your account and all associated data have been successfully deleted from ArborAlert.")
            
        except asyncio.TimeoutError:
            await interaction.user.send("Account deletion timed out. No changes were made to your account.")
            
    except Exception as e:
        await interaction.user.send(f"An error occurred while trying to delete your account: {e}")

# Change credentials command
async def change_credentials_command(bot, interaction):
    """Update your Arbor login credentials"""
    try:
        # Check if user exists in database
        if not user_exists(str(interaction.user.id)):
            await interaction.response.send_message("You need to set up an account first using the /setup command.", ephemeral=True)
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
            
            # Update credentials
            save_user_credentials(str(interaction.user.id), username, password)
            
            await interaction.user.send("Your Arbor credentials have been successfully updated! 🎉\n"
                                      "Please delete the messages where you sent your username and password for security.")
            
        except asyncio.TimeoutError:
            await interaction.user.send("The credential update process timed out. Please try again later.")
            
    except Exception as e:
        await interaction.user.send(f"An error occurred while updating your credentials: {e}")

# Debug command
async def debug_command(bot, interaction, full_test=False, cipher_suite=None):
    """Run diagnostic tests on the bot to identify issues"""
    try:
        # Check if user is authorized (can be expanded with admin checks)
        await interaction.response.defer(ephemeral=True)
        
        # Initialize debug tests
        debug_tests = DebugTests(bot, cipher_suite)
        
        # Run basic tests or full tests based on parameter
        if full_test:
            # For full tests, include user-specific tests with the full_test flag
            test_results = await debug_tests.run_all_tests(interaction, interaction.user.id, full_test=True)
        else:
            # Basic tests only
            test_results = await debug_tests.run_all_tests(interaction)
        
        # Send the consolidated results as a single message
        await interaction.followup.send(test_results, ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"An error occurred while running diagnostics: {str(e)}\n\nStack trace: ```\n{traceback.format_exc()}\n```", ephemeral=True)