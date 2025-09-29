#!/usr/bin/env python3
# -*--- coding: utf-8 characters ---*-
"""
Spice Summary Bot - Telegram bot for quick summaries
Had to rewrite this 3 times to get the conversation flow right

The state management was tricky to debug :|
"""

import logging
import time
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters

# My config setup - kept having path issues
import config
from summarizer import SpiceSummarizer

# Logging setup - copied from an old project
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for conversation flow
SELECTING_STYLE, PROCESSING_TEXT = range(2)

# Initialize our summarizer - this took forever to get right
summarizer = SpiceSummarizer()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - welcome message"""
    welcome_msg = """
Hey there! I'm Spice Summary! 🌶️📖

I can help you to quickly understand any article, text or URL. Just send me a URL or paste some text and I'll give you the key points.

What I do:
• Summarize articles or text
• Adjust for different readers (kids, engineers, etc.)
• Show the overall sentiment
• List the main points

Try /summarize to get started!
    """
    await update.message.reply_text(welcome_msg)


async def summarize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the summary process"""
    # Audience options - my friend suggested these categories
    audience_options = [['Kid', 'Engineer'], ['Scientist', 'Busy Worker']]

    await update.message.reply_text(
        "First, who's this summary for?",
        reply_markup=ReplyKeyboardMarkup(
            audience_options,
            one_time_keyboard=True,
            input_field_placeholder='Pick one'
        )
    )
    return SELECTING_STYLE


async def select_audience(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store audience choice and ask for content"""
    user_choice = update.message.text
    context.user_data['audience'] = user_choice.lower()

    await update.message.reply_text(
        f"Got it - summarizing for a {user_choice}!\n\nNow send me the text or a URL to summarize (max ~5000 words):",
        reply_markup=ReplyKeyboardRemove()
    )
    return PROCESSING_TEXT


async def process_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main processing function - this was the hardest part"""
    user_input = update.message.text
    audience = context.user_data.get('audience', 'general')

    # Let user know we're working on it focusfully :]
    wait_msg = await update.message.reply_text("🔄 Reading and analyzing the content ...")

    try:
        # First task is to check: if it's a URL or direct text
        if user_input.startswith(('http://', 'https://')):
            full_text = summarizer.extract_text_from_url(user_input)
        else:
            full_text = user_input

        # Length check - had issues with long texts crashing
        if summarizer.is_text_too_long(full_text):
            await update.message.reply_text("❌ Opps, Text is too long! Please, Keep it under 5000 words.")
            return ConversationHandler.END

        # Get the summary results
        results = summarizer.summarize(full_text, audience)

        # Format the response - tweaked this formatting several times
        response = f"""
**🌶️ Spice Summary for {audience.title()} 🌶️**

**Summary:**
{results['summary']}

**Mood:** {results['sentiment']}

**Main Points:**
"""
        for point in results['key_claims']:
            response += f"• {point}\n"

        response += "\n_Powered by Spice Summary_"

        await update.message.reply_text(response, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Processing error: {e}")
        await update.message.reply_text("😬 Sorry, something went wrong. Try again with different content.")
    finally:
        # Clean up the waiting message
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=wait_msg.message_id
        )

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the current operation"""
    await update.message.reply_text(
        'Cancelled! Use /summarize to start over.',
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


def main():
    """Main function - finally got this working after many attempts"""
    # Bot setup
    app = Application.builder().token(config.TOKEN).build()

    # Conversation handler - state management was confusing at first
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('summarize', summarize)],
        states={
            SELECTING_STYLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_audience)],
            PROCESSING_TEXT: [MessageHandler(filters.TEXT | filters.Entity("url"), process_content)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)

    # Start polling - the bot finally works!
    print("The Bot is running ...")
    app.run_polling()


if __name__ == '__main__':
    main()
