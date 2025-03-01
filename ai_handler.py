import re
import random
import discord
import asyncio
from embed_utils import create_basic_embed, COLORS
from database import user_exists

# Define patterns and responses for natural language processing
PATTERNS = {
    # Greeting patterns
    r"(?i)\b(hello|hi|hey|greetings|howdy|yo|hiya|morning|afternoon|evening)\b": [
        "Hello! How can I help you with ArborAlert today?",
        "Hi there! Need help with your assignments or reminders?",
        "Hey! I'm here to help you manage your Arbor assignments.",
        "Greetings! How can I assist with your school work today?",
        "Hi! Ready to help you stay on top of your assignments!"
    ],
    
    # Help patterns
    r"(?i)\b(help|assist|support|guide|how do (you|I)|what can you do|confused)\b": [
        "I can help you with several things! Try asking about:\n- Your assignments\n- Setting reminders\n- Checking due dates\n- Or use slash commands like /fetch, /setup, or /view_reminders",
        "Need assistance? You can ask me about your homework, reminders, or use any of the slash commands like /fetch.",
        "I'm here to help! I can fetch your assignments, set reminders, or help you manage your account. Just ask!",
        "I can assist with:\n✅ Fetching your homework\n⏰ Setting up reminders\n📝 Managing your account\n🔍 Finding specific assignments"
    ],
    
    # General assignment patterns
    r"(?i)\b(assignment|homework|task|due|coursework|project|deadline|work)\b": [
        "To see your assignments, you can use the /fetch command. If you want to be reminded about them, try /set_reminder.",
        "Looking for your assignments? Use /fetch to get them from Arbor, or ask me 'what assignments do I have?'",
        "I can help you keep track of your homework! Just ask me to fetch your assignments or set reminders.",
        "Need to check your coursework? I can fetch that information from Arbor for you!"
    ],
    
    # Fetch assignment patterns
    r"(?i)(what|show|get|fetch|find|tell me about|display) (my |the |)(assignments|homework|tasks|coursework|projects|work|deadlines)( do| have| are)? (i|me)( got| have| due| need to do)?\??": [
        "I'll check your assignments for you! Give me a moment...",
        "Let me fetch your assignments from Arbor right away!",
        "I'll retrieve your homework information now!",
        "Checking Arbor for your assignments..."
    ],
    
    # Due date specific patterns
    r"(?i)(what('s| is)|when are) (my |the |)(assignments|homework|tasks|coursework|projects) due\??": [
        "I'll check when your assignments are due. One moment...",
        "Let me fetch your due dates from Arbor right away!",
        "I'll find out when your homework is due."
    ],
    
    # General reminder patterns
    r"(?i)\b(remind|reminder|notify|alert|notification)\b": [
        "You can set reminders using the /set_reminder command followed by the number of days before the due date.",
        "Need to be reminded about assignments? Use /set_reminder or ask me to 'set a reminder for 2 days before'.",
        "I can notify you before assignments are due. Just tell me how many days in advance you want to be reminded.",
        "Reminders help you stay on top of your work! Tell me when you want to be notified about upcoming deadlines."
    ],
    
    # Set reminder patterns
    r"(?i)(set|create|make|configure|establish) (a |an |)(reminder|alert|notification) (for|of|at) (\d+) day": [
        "I'll set your reminder for {0} days before assignments are due.",
        "Setting your reminder to {0} days before due dates.",
        "Got it! You'll be reminded {0} days before each assignment is due.",
        "I've configured your reminders for {0} days before deadlines."
    ],
    
    # View reminder patterns
    r"(?i)(view|show|check|list|see|display|what are) (my |the |)(reminders|alerts|notifications|upcoming reminders)": [
        "I'll show you your upcoming reminders. One moment...",
        "Let me check what reminders you have set up...",
        "Retrieving your reminder settings and upcoming notifications...",
        "I'll display all your active reminders now."
    ],
    
    # Setup account patterns
    r"(?i)(setup|create|register|add|start|begin|initialize|make) (my |an |a |)(account|profile|registration|login)": [
        "I'll help you set up your ArborAlert account. Let's get started!",
        "Let's set up your account so you can access your assignments.",
        "I'll guide you through the account creation process.",
        "Let's get you registered so you can start tracking your assignments!"
    ],
    
    # Change credentials patterns
    r"(?i)(change|update|modify|edit|alter|reset) (my |the |)(credentials|password|login|email|account details|login info)": [
        "I'll help you update your Arbor login credentials.",
        "Let's update your account information.",
        "I can help you change your login details. Let's do that now.",
        "I'll guide you through updating your account credentials."
    ],
    
    # Delete account patterns
    r"(?i)(delete|remove|erase|get rid of|deactivate) (my |the |)(account|profile|data|information)": [
        "I can help you delete your account. This will remove all your data from ArborAlert.",
        "I'll assist you with removing your account and all associated data.",
        "I can guide you through the account deletion process. This action cannot be undone.",
        "I'll help you remove your account from our system."
    ],
    
    # Debug patterns
    r"(?i)(debug|diagnose|test|troubleshoot|fix|repair|check|something('s| is) wrong) (with |)(the |my |)(bot|system|account|app|program)": [
        "I'll run a diagnostic test to identify any issues with the system.",
        "Let me check if everything is working correctly with your account.",
        "I'll troubleshoot the system to find any problems.",
        "Let's run some diagnostics to see what might be going wrong."
    ],
    
    # Status inquiry patterns
    r"(?i)(how are you|how('s| is) it going|what('s| is) up|how do you feel)": [
        "I'm functioning well and ready to help with your assignments! How can I assist you today?",
        "I'm operational and at your service! Need help with homework or reminders?",
        "All systems running smoothly! What can I help you with today?",
        "I'm here and ready to assist with your Arbor assignments!"
    ],
    
    # Capability inquiry patterns
    r"(?i)(what can you do|what are you capable of|what are your features|what do you do)": [
        "I can help you manage your Arbor assignments! I can fetch homework, set reminders, and help you manage your account.",
        "My main functions include:\n✅ Fetching assignments from Arbor\n⏰ Setting up reminders for due dates\n📝 Managing your account\n🔍 Answering questions about your homework",
        "I'm designed to help you stay on top of your school work by connecting to Arbor and managing your assignments and reminders."
    ],
    
    # Gratitude patterns
    r"(?i)\b(thank|thanks|thx|appreciate|grateful)\b": [
        "You're welcome! Is there anything else I can help with?",
        "Happy to help! Let me know if you need anything else.",
        "No problem! Good luck with your assignments!",
        "Glad I could assist! Feel free to ask if you need more help.",
        "You're welcome! I'm here whenever you need help with your assignments."
    ],
    
    # Farewell patterns
    r"(?i)\b(bye|goodbye|see you|later|farewell|cya|ttyl)\b": [
        "Goodbye! Come back if you need help with your assignments!",
        "See you later! Don't forget to check your reminders!",
        "Bye! Good luck with your studies!",
        "Take care! I'll be here when you need to check on your assignments again.",
        "Farewell! Remember to stay on top of those deadlines!"
    ],
    
    # Confusion or frustration patterns
    r"(?i)(i('m| am) (confused|lost|stuck|frustrated)|this isn't working|doesn't work|can't understand)": [
        "I'm sorry to hear that. Let me try to help. You can use commands like /help or ask me specific questions about assignments or reminders.",
        "Let's figure this out together. What specifically are you trying to do with ArborAlert?",
        "I understand it can be frustrating. Would you like me to run a diagnostic test to see if there are any issues?",
        "I'm here to help! Could you tell me more about what you're trying to accomplish?"
    ],
    
    # Subject-specific homework inquiries
    r"(?i)(do i have|what|any) (homework|assignments|tasks|work) (for|in|on) (math|english|science|history|geography|art|music|pe|physics|chemistry|biology)": [
        "Let me check if you have any assignments in that subject. I'll need to fetch your current assignments...",
        "I can look for subject-specific homework. Let me retrieve your assignments...",
        "I'll check your assignments and filter for that subject. One moment..."
    ]
}

# Base class for mock interactions
class BaseMockInteraction:
    def __init__(self, message, response_msg):
        self.user = message.author
        self.channel = message.channel
        self.response_msg = response_msg
        self.response = self
        self.followup = self
        self._response_done = False
        
    async def send(self, content=None, embed=None, ephemeral=False):
        await self.response_msg.edit(content=content, embed=embed)
        self._response_done = True
        
    async def send_message(self, content=None, embed=None, ephemeral=False):
        await self.response_msg.edit(content=content, embed=embed)
        self._response_done = True
        
    async def response_send_message(self, content=None, embed=None, ephemeral=False):
        await self.response_msg.edit(content=content, embed=embed)
        self._response_done = True
        
    async def response_defer(self, ephemeral=False):
        self._response_done = True
        pass
        
    # Add defer method to handle the call in fetch_command
    async def defer(self, ephemeral=False):
        # This is a no-op since we're already showing a message
        self._response_done = True
        pass
        
    def is_done(self):
        return self._response_done
        
    async def followup_send(self, content=None, embed=None, ephemeral=False):
        await self.response_msg.edit(content=content, embed=embed)
        
    # Make sure we have a proper implementation for the send method on followup
    async def send(self, content=None, embed=None, ephemeral=False):
        await self.response_msg.edit(content=content, embed=embed)

# Function to process natural language input
async def process_message(message, bot):
    """Process natural language messages and respond accordingly"""
    content = message.content.lower()
    user_id = str(message.author.id)
    
    # Don't respond to bot messages
    if message.author.bot:
        return
        
    # Only require bot mention if not in DMs
    if not isinstance(message.channel, discord.DMChannel) and not bot.user.mentioned_in(message):
        return
    
    # Remove the bot mention from the message
    content = content.replace(f'<@{bot.user.id}>', '').strip()
    
    # Check if user exists in database before processing commands that require an account
    user_registered = user_exists(user_id)
    
    # Extract potential subject from message for subject-specific queries
    subjects = ["math", "english", "science", "history", "geography", "art", "music", "pe", 
               "physics", "chemistry", "biology", "computer science", "french", "spanish", "german"]
    mentioned_subject = None
    for subject in subjects:
        if subject in content:
            mentioned_subject = subject
            break
    
    # Check for command-like patterns
    for pattern, responses in PATTERNS.items():
        match = re.search(pattern, content)
        if match:
            # Handle special cases that require actions
            
            # Assignment related actions - expanded to catch more variations
            if ("assignment" in pattern or "homework" in pattern) and ("what" in pattern or "show" in pattern or "get" in pattern or "fetch" in pattern) and match:
                if not user_registered:
                    await send_registration_required(message)
                    return
                await handle_fetch_request(message, bot)
                return
                
            # Subject-specific homework inquiries
            elif mentioned_subject and ("homework" in content or "assignment" in content or "work" in content or "task" in content):
                if not user_registered:
                    await send_registration_required(message)
                    return
                # We'll still use the regular fetch but inform the user to look for that subject
                embed = create_basic_embed("Subject-Specific Homework", 
                                          f"I'll fetch all your assignments. Please look for {mentioned_subject.capitalize()} in the results.", 
                                          "info")
                await message.channel.send(embed=embed)
                await handle_fetch_request(message, bot)
                return
                
            # Due date specific inquiries
            elif ("due" in pattern or "deadline" in pattern) and match:
                if not user_registered:
                    await send_registration_required(message)
                    return
                await handle_fetch_request(message, bot)
                return
                
            # Reminder related actions - improved pattern matching
            elif ("set" in pattern or "create" in pattern) and ("reminder" in pattern or "alert" in pattern) and match:
                if not user_registered:
                    await send_registration_required(message)
                    return
                # Extract the number of days from the match
                # The group index might vary based on the regex pattern
                days_group = None
                for i in range(len(match.groups())):
                    group = match.group(i+1)
                    if group and group.isdigit():
                        days_group = int(group)
                        break
                
                if days_group:
                    await handle_set_reminder(message, bot, days_group)
                else:
                    # Default to 1 day if we couldn't extract a number
                    await handle_set_reminder(message, bot, 1)
                return
                
            elif ("view" in pattern or "show" in pattern or "check" in pattern or "list" in pattern) and ("reminder" in pattern or "alert" in pattern) and match:
                if not user_registered:
                    await send_registration_required(message)
                    return
                await handle_view_reminders(message, bot)
                return
                
            # Account management actions - improved pattern matching
            elif ("setup" in pattern or "create" in pattern or "register" in pattern) and ("account" in pattern or "profile" in pattern) and match:
                await handle_setup(message, bot)
                return
                
            elif ("change" in pattern or "update" in pattern or "modify" in pattern) and ("credentials" in pattern or "password" in pattern or "login" in pattern) and match:
                if not user_registered:
                    await send_registration_required(message)
                    return
                await handle_change_credentials(message, bot)
                return
                
            elif ("delete" in pattern or "remove" in pattern) and ("account" in pattern or "profile" in pattern) and match:
                if not user_registered:
                    await send_registration_required(message)
                    return
                await handle_delete_account(message, bot)
                return
                
            # Debug actions
            elif ("debug" in pattern or "diagnose" in pattern or "test" in pattern or "troubleshoot" in pattern) and match:
                await handle_debug(message, bot)
                return
                
            # Help actions
            elif ("help" in pattern or "guide" in pattern or "how" in pattern or "what can you do" in pattern) and match:
                await handle_help(message, bot)
                return
            
            # For simple responses
            response = random.choice(responses)
            
            # Format response if it contains placeholders
            if match.groups() and '{0}' in response:
                # Find the first numeric group to use for formatting
                for i in range(len(match.groups())):
                    group = match.group(i+1)
                    if group and group.isdigit():
                        response = response.format(group)
                        break
                
            embed = create_basic_embed("ArborAlert Assistant", response, "info")
            await message.channel.send(embed=embed)
            return
    
    # Default response if no pattern matches - more varied responses
    default_responses = [
        "I'm not sure I understand. Try asking about assignments, reminders, or use slash commands like /fetch.",
        "I didn't quite catch that. You can ask me about your homework, reminders, or use commands like /setup.",
        "Sorry, I'm not sure how to help with that. Try asking about assignments or reminders.",
        "I'm having trouble understanding your request. Could you rephrase it or try using one of the slash commands?",
        "I'm still learning! Try asking me about your assignments, setting reminders, or managing your account.",
        "Hmm, I'm not sure what you're asking for. You can say things like 'show my assignments' or 'set a reminder for 2 days'."
    ]
    embed = create_basic_embed("ArborAlert Assistant", random.choice(default_responses), "info")
    await message.channel.send(embed=embed)

# Handler functions for specific actions
async def handle_fetch_request(message, bot):
    """Handle a natural language request to fetch assignments"""
    from bot_commands import fetch_command
    
    # Create a mock interaction for the fetch command
    embed = create_basic_embed("Fetching Assignments", "I'm retrieving your assignments from Arbor...", "info")
    response_msg = await message.channel.send(embed=embed)
    
    # Use the BaseMockInteraction class
    mock_interaction = BaseMockInteraction(message, response_msg)
    
    # Call the fetch command with our mock interaction
    try:
        await fetch_command(mock_interaction)
    except Exception as e:
        embed = create_basic_embed("Error", f"I encountered an error while fetching your assignments: {str(e)}", "error")
        await response_msg.edit(embed=embed)

async def handle_set_reminder(message, bot, days):
    """Handle a natural language request to set reminder days"""
    from bot_commands import set_reminder_command
    
    embed = create_basic_embed("Setting Reminder", f"I'm setting your reminder to {days} days before due dates...", "info")
    response_msg = await message.channel.send(embed=embed)
    
    # Use the BaseMockInteraction class
    mock_interaction = BaseMockInteraction(message, response_msg)
    
    # Call the set_reminder command with our mock interaction
    try:
        await set_reminder_command(mock_interaction, days)
    except Exception as e:
        embed = create_basic_embed("Error", f"I encountered an error while setting your reminder: {str(e)}", "error")
        await response_msg.edit(embed=embed)

async def handle_view_reminders(message, bot):
    """Handle a natural language request to view reminders"""
    from bot_commands import view_reminders_command
    
    embed = create_basic_embed("Checking Reminders", "I'm retrieving your reminders...", "info")
    response_msg = await message.channel.send(embed=embed)
    
    # Use the BaseMockInteraction class
    mock_interaction = BaseMockInteraction(message, response_msg)
    
    # Call the view_reminders command with our mock interaction
    try:
        await view_reminders_command(mock_interaction)
    except Exception as e:
        embed = create_basic_embed("Error", f"I encountered an error while retrieving your reminders: {str(e)}", "error")
        await response_msg.edit(embed=embed)

async def handle_setup(message, bot):
    """Handle a natural language request to setup an account"""
    from bot_commands import setup_command
    
    embed = create_basic_embed("Account Setup", "I'll help you set up your ArborAlert account...", "info")
    response_msg = await message.channel.send(embed=embed)
    
    # Use the BaseMockInteraction class
    mock_interaction = BaseMockInteraction(message, response_msg)
    
    try:
        await setup_command(bot, mock_interaction)
    except Exception as e:
        embed = create_basic_embed("Error", f"I encountered an error during account setup: {str(e)}", "error")
        await response_msg.edit(embed=embed)

async def handle_change_credentials(message, bot):
    """Handle a natural language request to change account credentials"""
    from bot_commands import change_credentials_command
    
    embed = create_basic_embed("Update Credentials", "I'll help you update your Arbor login credentials...", "info")
    response_msg = await message.channel.send(embed=embed)
    
    # Use the BaseMockInteraction class
    mock_interaction = BaseMockInteraction(message, response_msg)
    
    try:
        await change_credentials_command(bot, mock_interaction)
    except Exception as e:
        embed = create_basic_embed("Error", f"I encountered an error while updating credentials: {str(e)}", "error")
        await response_msg.edit(embed=embed)

async def handle_delete_account(message, bot):
    """Handle a natural language request to delete an account"""
    from bot_commands import delete_account_command
    
    embed = create_basic_embed("Delete Account", "I'll help you delete your ArborAlert account...", "info")
    response_msg = await message.channel.send(embed=embed)
    
    # Use the BaseMockInteraction class
    mock_interaction = BaseMockInteraction(message, response_msg)
    
    try:
        await delete_account_command(bot, mock_interaction)
    except Exception as e:
        embed = create_basic_embed("Error", f"I encountered an error while deleting your account: {str(e)}", "error")
        await response_msg.edit(embed=embed)

async def handle_debug(message, bot):
    """Handle a natural language request to run diagnostics"""
    from bot_commands import debug_command
    
    embed = create_basic_embed("Diagnostics", "Running system diagnostics...", "info")
    response_msg = await message.channel.send(embed=embed)
    
    # Use the BaseMockInteraction class
    mock_interaction = BaseMockInteraction(message, response_msg)
    
    try:
        await debug_command(bot, mock_interaction)
    except Exception as e:
        embed = create_basic_embed("Error", f"I encountered an error while running diagnostics: {str(e)}", "error")
        await response_msg.edit(embed=embed)

async def send_registration_required(message):
    """Send a message informing the user they need to register first"""
    embed = create_basic_embed(
        "Registration Required", 
        "You need to set up your account first. Please use the /setup command or say 'setup account' to get started.", 
        "warning"
    )
    await message.channel.send(embed=embed)

async def handle_help(message, bot):
    """Handle a natural language request for help"""
    from help_command import help_command
    
    embed = create_basic_embed("Help Guide", "Let me show you how to use ArborAlert...", "info")
    response_msg = await message.channel.send(embed=embed)
    
    # Use the BaseMockInteraction class
    mock_interaction = BaseMockInteraction(message, response_msg)
    
    try:
        await help_command(mock_interaction)
    except Exception as e:
        embed = create_basic_embed("Error", f"I encountered an error while displaying help: {str(e)}", "error")
        await response_msg.edit(embed=embed)