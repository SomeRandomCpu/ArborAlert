import discord
from embed_utils import create_basic_embed

async def help_command(interaction: discord.Interaction):
    """Display detailed help information about ArborAlert's commands and AI capabilities"""
    help_embed = create_basic_embed(
        "ArborAlert Help Guide",
        "Welcome to ArborAlert! I can help you manage your assignments in two ways:\n\n" +
        "🤖 **AI Natural Language**\nYou can talk to me naturally! Just type your message and I'll understand. For example:\n\n" +
        "• *'What homework do I have?'*\n" +
        "• *'Set a reminder for 3 days before deadlines'*\n" +
        "• *'Show me my upcoming reminders'*\n" +
        "• *'Help me set up my account'*\n" +
        "• *'Update my login details'*\n\n" +
        "🔧 **Slash Commands**\nYou can also use these precise commands:\n\n" +
        "**/setup**\nSet up your Arbor account credentials\n" +
        "**/fetch**\nGet your current homework assignments\n" +
        "**/set_reminder [days]**\nSet how many days before due dates to be reminded\n" +
        "**/view_reminders**\nSee all your upcoming assignment reminders\n" +
        "**/change_credentials**\nUpdate your Arbor login information\n" +
        "**/delete_account**\nRemove your account and data\n" +
        "**/debug**\nRun diagnostics if you're having issues\n\n" +
        "💡 **Pro Tips**\n" +
        "• The AI understands many variations of these commands\n" +
        "• You can ask about assignments in different ways\n" +
        "• If you're unsure, just ask for help naturally!",
        "info"
    )
    await interaction.response.send_message(embed=help_embed, ephemeral=True)