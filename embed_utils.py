import discord
import datetime

# Define color constants for different message types
COLORS = {
    "success": 0x57F287,  # Green
    "warning": 0xFEE75C,  # Yellow
    "error": 0xED4245,    # Red
    "info": 0x5865F2,     # Blue
    "reminder": 0xEB459E,  # Pink
    "default": 0x9B59B6   # Purple
}

# Custom emojis for different assignment statuses
EMOJIS = {
    "overdue": "⚠️",
    "due_soon": "⏰",
    "completed": "✅",
    "in_progress": "🔄",
    "reminder": "🔔"
}

# Create a basic embed with consistent styling
def create_basic_embed(title, description=None, color="default"):
    """Create a basic Discord embed with consistent styling"""
    embed = discord.Embed(
        title=title,
        description=description,
        color=COLORS[color],
        timestamp=datetime.datetime.now()
    )
    embed.set_footer(text="ArborAlert")
    return embed

# Create an embed for assignments
def create_assignments_embed(assignments_text):
    """Convert plain text assignments into a rich embed format"""
    embed = create_basic_embed("Your Assignments", color="info")
    
    # Split the text by lines to process each assignment
    lines = assignments_text.split('\n')
    current_section = None
    current_content = ""
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this is a section header
        if "Overdue" in line:
            # If we have content from a previous section, add it
            if current_section and current_content:
                embed.add_field(name=current_section, value=current_content, inline=False)
            current_section = f"{EMOJIS['overdue']} Overdue Assignments"
            current_content = ""
        elif "Assignments that are due" in line:
            # If we have content from a previous section, add it
            if current_section and current_content:
                embed.add_field(name=current_section, value=current_content, inline=False)
            current_section = f"{EMOJIS['due_soon']} Upcoming Assignments"
            current_content = ""
        else:
            # This is assignment content
            # Format assignment entries with subject code in bold
            subject_match = line.split(':', 1)
            if len(subject_match) > 1 and '/' in subject_match[0]:
                subject_code = subject_match[0].strip()
                assignment_details = subject_match[1].strip()
                formatted_line = f"**{subject_code}:** {assignment_details}\n"
                current_content += formatted_line
            else:
                current_content += f"{line}\n"
    
    # Add the last section if there's content
    if current_section and current_content:
        embed.add_field(name=current_section, value=current_content, inline=False)
        
    return embed

# Create an embed for reminders
def create_reminder_embed(assignment, due_date):
    """Create a rich embed for assignment reminders"""
    embed = create_basic_embed(
        f"{EMOJIS['reminder']} Assignment Reminder", 
        f"You have an upcoming assignment due!", 
        "reminder"
    )
    
    # Extract subject code if available
    subject_code = assignment.split(':', 1)[0] if ':' in assignment else "Assignment"
    assignment_name = assignment.split(':', 1)[1].strip() if ':' in assignment else assignment
    
    embed.add_field(name="Subject", value=subject_code, inline=True)
    embed.add_field(name="Assignment", value=assignment_name, inline=True)
    embed.add_field(name="Due Date", value=due_date, inline=True)
    
    return embed

# Create an embed for user reminders list
def create_reminders_list_embed(reminders):
    """Create a rich embed showing all upcoming reminders"""
    embed = create_basic_embed(
        "Your Upcoming Reminders", 
        "Here are all your scheduled assignment reminders:", 
        "info"
    )
    
    if not reminders:
        embed.description = "You don't have any upcoming reminders."
        return embed
    
    # Group reminders by due date
    reminders_by_date = {}
    for assignment, due_date, reminder_date in reminders:
        if due_date not in reminders_by_date:
            reminders_by_date[due_date] = []
        reminders_by_date[due_date].append((assignment, reminder_date))
    
    # Add fields for each due date
    for due_date, assignments in sorted(reminders_by_date.items()):
        assignments_text = ""
        for assignment, reminder_date in assignments:
            assignments_text += f"• **{assignment}**\n  _Reminder on: {reminder_date}_\n"
        
        embed.add_field(
            name=f"📅 Due on {due_date}",
            value=assignments_text,
            inline=False
        )
    
    return embed

# Create an embed for welcome message
def create_welcome_embed(username):
    """Create a welcome embed for new users"""
    embed = create_basic_embed(
        "Welcome to ArborAlert! 🎉", 
        "Your homework assistant is ready to help you stay on top of your assignments.", 
        "success"
    )
    
    embed.add_field(
        name="Account Setup",
        value=f"Your account has been successfully set up with username: **{username}**\n"
              f"Please delete the messages where you sent your credentials for security.",
        inline=False
    )
    
    embed.add_field(
        name="Getting Started",
        value="• The bot fetches your homework automatically once a day\n"
              "• Use `/fetch` to manually check your assignments\n"
              "• Use `/set_reminder` to customize when you get notified\n"
              "• Use `/view_reminders` to see your upcoming reminders",
        inline=False
    )
    
    embed.add_field(
        name="Need Help?",
        value="Send a message in the arboralert-support channel if you have any issues!",
        inline=False
    )
    
    return embed

# Create an error embed
def create_error_embed(error_message):
    """Create an embed for error messages"""
    embed = create_basic_embed("Error Occurred", error_message, "error")
    return embed

# Create a confirmation embed
def create_confirmation_embed(title, description):
    """Create an embed for confirmation messages"""
    embed = create_basic_embed(title, description, "warning")
    embed.set_footer(text="Reply with 'yes' to confirm or 'no' to cancel")
    return embed