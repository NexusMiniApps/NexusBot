from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application,ApplicationBuilder, CallbackContext, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import json
import logging
import os

if os.path.exists(".env"):
    # if we see the .env file, load it
    from dotenv import load_dotenv
    load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
BOT_USERNAME = os.getenv('BOT_USERNAME')

# Defaults to local dev environment
ENDPOINT = os.getenv("DEV_URL")
if ENDPOINT is None:
    ENDPOINT = os.getenv('LIVE_URL')


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


# ngrok http --domain=electric-peacock-nearly.ngrok-free.app 3000

async def start_command(update: Update, context: CallbackContext):
    # Test bot interface by showing google for now
    kb = [
        [InlineKeyboardButton("Create a meeting!", web_app=WebAppInfo("https://nexusmeet.vercel.app/new-meeting"))]
    ]

    await update.message.reply_text("Where you headed?", reply_markup=InlineKeyboardMarkup(kb))

async def test_command(update: Update, context: CallbackContext):
    await update.message.reply_text("Test command executed")
    user_says = " ".join(context.args)
    await update.message.reply_text("You said: " + user_says)

async def handle_message(update: Update, callback: CallbackContext):
    text = str(update.message.text).lower()
    await update.message.reply_text(f"Your message was: {text}")

async def web_app_data(update: Update, context: CallbackContext):
    data = json.loads(update.message.web_app_data.data)
    await update.message.reply_text("Your data was:")
    await update.message.reply_text(data)


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    await query.answer()

    await query.edit_message_text(text=f"Selected option: {query.data}")

# Sets the bot commands
async def post_init(application: Application) -> None:
    await application.bot.set_my_commands([('start', 'Starts the bot'), ('test', 'Test the bot')])

if __name__ == '__main__':
    # Run app builder
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    # Command Handlers
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('test', test_command))
    
    # Message Handlers
    application.add_handler(MessageHandler(filters.Text, handle_message))

    # Web App Data Handler
    # application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))   
    # application.add_handler(CallbackQueryHandler(button))
    
    # Run the bot 
    application.run_polling()
    