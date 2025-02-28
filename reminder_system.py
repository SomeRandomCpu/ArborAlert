import datetime
import asyncio
import schedule
import time
from threading import Thread
from database import get_due_reminders, mark_reminder_sent, get_all_users
from arbor_processor import process_arbor_data
from embed_utils import create_reminder_embed

# Function to run the scheduler
def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

# Schedule daily fetch for all users
def schedule_daily_fetch():
    users = get_all_users()
    
    for user in users:
        discord_id = user[0]
        try:
            process_arbor_data(discord_id)
        except Exception as e:
            print(f"Error fetching data for user {discord_id}: {e}")

# Initialize scheduler
def init_scheduler():
    # Schedule the daily fetch at 7 AM
    schedule.every().day.at("07:00").do(schedule_daily_fetch)
    
    # Start the scheduler in a separate thread
    scheduler_thread = Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()

# Background task to check for reminders
async def check_reminders(bot):
    while True:
        try:
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            
            # Get reminders due today
            reminders = get_due_reminders(today)
            
            for discord_id, assignment, due_date in reminders:
                try:
                    user = await bot.fetch_user(int(discord_id))
                    
                    # Create a rich embed for the reminder
                    embed = create_reminder_embed(assignment, due_date)
                    await user.send(embed=embed)
                    
                    # Mark reminder as sent
                    mark_reminder_sent(discord_id, assignment, due_date)
                except Exception as e:
                    print(f"Error sending reminder to user {discord_id}: {e}")
            
        except Exception as e:
            print(f"Error checking reminders: {e}")
        
        # Check every hour
        await asyncio.sleep(3600)