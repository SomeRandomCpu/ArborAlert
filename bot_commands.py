import discord
import asyncio
import os
import traceback
from database import save_user_credentials, get_user_reminders, set_reminder_days, delete_user_account, user_exists
from arbor_processor import process_arbor_data
from debug_utils import DebugTests, get_system_info
from embed_utils import (
    create_basic_embed, create_assignments_embed, create_reminders_list_embed,
    create_welcome_embed, create_error_embed, create_confirmation_embed
)

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

        # Send welcome message with rich embed
        welcome_embed = create_welcome_embed(username)
        await interaction.user.send(embed=welcome_embed)

        # Automatically fetch homework after setup
        try:
            process_arbor_data(str(interaction.user.id))
            
            # Read and send the processed text
            with open("arbor_processed_text.txt", "r", encoding="utf-8") as file:
                text = file.read()
            
            # Create a rich embed for assignments
            assignments_embed = create_assignments_embed(text)
            await interaction.user.send(embed=assignments_embed)
        except Exception as e:
            error_embed = create_error_embed(f"Could not automatically fetch your assignments: {e}\nYou can try manually using the /fetch command.")
            await interaction.user.send(embed=error_embed)
        finally:
            # Cleanup temporary files
            if os.path.exists("arbor_text.txt"):
                os.remove("arbor_text.txt")
            if os.path.exists("arbor_processed_text.txt"):
                os.remove("arbor_processed_text.txt")
    except Exception as e:
        error_embed = create_error_embed(f"I encountered an error during account setup: {e}")
        await interaction.user.send(embed=error_embed)

# Fetch command
async def fetch_command(interaction):
    try:
        await interaction.response.defer()
        process_arbor_data(str(interaction.user.id))
        
        # Read the processed text and send it to the user
        try:
            with open("arbor_processed_text.txt", "r", encoding="utf-8") as file:
                text = file.read()

            # Create a rich embed for assignments
            assignments_embed = create_assignments_embed(text)
            await interaction.user.send(embed=assignments_embed)

            # Follow up on the original interaction
            success_embed = create_basic_embed("Success!", "Your assignments have been fetched successfully.", "success")
            await interaction.followup.send(embed=success_embed, ephemeral=True)
        except FileNotFoundError:
            error_embed = create_error_embed("The processed text file was not found.")
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            return
    except Exception as e:
        error_embed = create_error_embed(f"I encountered an error while fetching your assignments: {e}")
        await interaction.followup.send(embed=error_embed, ephemeral=True)
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
        success_embed = create_basic_embed(
            "Reminder Set", 
            f"You will now be reminded {days_before} day(s) before assignments are due.", 
            "success"
        )
        await interaction.response.send_message(embed=success_embed, ephemeral=True)
    except Exception as e:
        error_embed = create_error_embed(f"I encountered an error while retrieving your reminders: {e}")
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

# View reminders command
async def view_reminders_command(interaction):
    """View your upcoming assignment reminders"""
    try:
        reminders = get_user_reminders(str(interaction.user.id))
        
        # Create a rich embed for the reminders list
        reminders_embed = create_reminders_list_embed(reminders)
        await interaction.response.send_message(embed=reminders_embed, ephemeral=True)
    except Exception as e:
        error_embed = create_error_embed(f"I encountered an error while retrieving your reminders: {e}")
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

# Delete account command
async def delete_account_command(bot, interaction):
    """Delete your account and all associated data from ArborAlert"""
    try:
        # Check if user exists in database
        if not user_exists(str(interaction.user.id)):
            error_embed = create_error_embed("You don't have an account to delete.")
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return
        
        # Confirm deletion with user
        confirmation_embed = create_confirmation_embed(
            "⚠️ Account Deletion", 
            "This will permanently delete your account and all your reminders from ArborAlert.\n"
            "Your data cannot be recovered after deletion.\n\n"
            "Are you sure you want to proceed? Reply with 'yes' to confirm or 'no' to cancel."
        )
        await interaction.response.send_message(embed=confirmation_embed, ephemeral=True)
        
        def check_confirmation(m):
            return m.author == interaction.user and isinstance(m.channel, discord.DMChannel) and \
                   m.content.lower() in ['yes', 'no']
        
        try:
            confirmation = await bot.wait_for("message", check=check_confirmation, timeout=60)
            
            if confirmation.content.lower() == 'no':
                cancel_embed = create_basic_embed("Cancelled", "Account deletion cancelled.", "info")
                await interaction.user.send(embed=cancel_embed)
                return
            
            # Delete user data
            delete_user_account(str(interaction.user.id))
            
            success_embed = create_basic_embed(
                "Account Deleted", 
                "Your account and all associated data have been successfully deleted from ArborAlert.", 
                "success"
            )
            await interaction.user.send(embed=success_embed)
            
        except asyncio.TimeoutError:
            timeout_embed = create_basic_embed(
                "Timeout", 
                "Account deletion timed out. No changes were made to your account.", 
                "warning"
            )
            await interaction.user.send(embed=timeout_embed)
            
    except Exception as e:
        error_embed = create_error_embed(f"I encountered an error while deleting your account: {e}")
        await interaction.user.send(embed=error_embed)

# Change credentials command
async def change_credentials_command(bot, interaction):
    """Update your Arbor login credentials"""
    try:
        # Check if user exists in database
        if not user_exists(str(interaction.user.id)):
            error_embed = create_error_embed("You need to set up an account first using the /setup command.")
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return
        
        info_embed = create_basic_embed("Update Credentials", "I'll help you update your Arbor credentials. Please check your DMs.", "info")
        await interaction.response.send_message(embed=info_embed, ephemeral=True)
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
            
            success_embed = create_basic_embed(
                "Credentials Updated", 
                "Your Arbor credentials have been successfully updated! 🎉\n"
                "Please delete the messages where you sent your username and password for security.", 
                "success"
            )
            await interaction.user.send(embed=success_embed)
            
        except asyncio.TimeoutError:
            timeout_embed = create_basic_embed(
                "Timeout", 
                "The credential update process timed out. Please try again later.", 
                "warning"
            )
            await interaction.user.send(embed=timeout_embed)
            
    except Exception as e:
        error_embed = create_error_embed(f"I encountered an error while updating credentials: {e}")
        await interaction.user.send(embed=error_embed)

# Debug command
async def debug_command(bot, interaction, full_test=False, cipher_suite=None, test_error=None):
    """Run diagnostic tests on the bot to identify issues"""
    try:
        # Check if a test error message was provided
        if test_error:
            # Simulate an error for testing purposes
            error_embed = create_error_embed(f"TEST ERROR: {test_error}")
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return
            
        # Initialize debug tests
        debug_tests = DebugTests(bot, cipher_suite)
        
        # Show initial status message
        info_embed = create_basic_embed(
            "Running Diagnostics", 
            "Running diagnostic tests on ArborAlert. This may take a moment...", 
            "info"
        )
        await interaction.response.send_message(embed=info_embed, ephemeral=True)
        
        # Run basic tests or full tests based on parameter
        if full_test:
            # For full tests, include user-specific tests with the full_test flag
            test_results = await debug_tests.run_all_tests(interaction, interaction.user.id, full_test=True)
        else:
            # Basic tests only
            test_results = await debug_tests.run_all_tests(interaction)
        
        # Send the consolidated results as a followup message
        await interaction.followup.send(test_results, ephemeral=True)
    except Exception as e:
        error_embed = create_error_embed(f"I encountered an error while running diagnostics: {e}")
        
        # Check if the initial response has been sent
        if interaction.response.is_done():
            await interaction.followup.send(embed=error_embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=error_embed, ephemeral=True)