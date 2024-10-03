from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackContext, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode
import json
import logging
import os
import asyncio
from supabase import create_client, Client

# Replace these with your actual Supabase project URL and API key

# Initialize the Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

if os.path.exists(".env"):
    # if we see the .env file, load it
    from dotenv import load_dotenv
    load_dotenv()


BOT_TOKEN = os.getenv('BOT_TOKEN')
MINI_APP_URL = os.getenv('MINI_APP_URL')
BOT_URL = os.getenv('BOT_URL','https://t.me/NexusMiniApps_Bot/NexusMeet')
APP_URL = os.getenv('APP_URL', "https://nexusmeet.vercel.app/new-meeting")
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')


# Defaults to local dev environment
ENDPOINT = os.getenv("DEV_URL")
if ENDPOINT is None:
    ENDPOINT = os.getenv('LIVE_URL')
    
VOTE_ENDPOINT= os.getenv("VOTE_ENDPOINT")
SHARE_ENDPOINT = os.getenv("SHARE_ENDPOINT")


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ngrok http --domain=electric-peacock-nearly.ngrok-free.app 3000

async def start_command(update: Update, context: CallbackContext):
    kb = [
        [InlineKeyboardButton("Show me stagemate!", web_app=WebAppInfo('https://www.google.com'))],
    ]

    await update.message.reply_text("Where you headed?", reply_markup=InlineKeyboardMarkup(kb))



# Dictionary to store event data
events = {}
async def echo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide an event name after /echo.")
        return

    event_name = " ".join(context.args)
    user = update.effective_user
    user_mention = user.mention_html()
    
    # Create a unique identifier for this event
    event_id = f"{update.effective_chat.id}_{update.message.message_id}"
    
    # Initialize event data
    events[event_id] = {
        "name": event_name,
        "vote_count": 0,
        "share_count": 0,
        "voters": set(),
        "sharers": set()
    }
    
    # keyboard = [
    #     [InlineKeyboardButton(f"Vote for your favourite idea! (0)", callback_data=f"vote_{event_id}")],
    #     [InlineKeyboardButton(f"Share your idea! (0)", callback_data=f"share_{event_id}")]
    # ]
    
    kb = [
        [InlineKeyboardButton("Vote for your idea!", web_app=WebAppInfo(VOTE_ENDPOINT))],
        [InlineKeyboardButton("Share your idea!", web_app=WebAppInfo(SHARE_ENDPOINT))]
    ]
    reply_markup = InlineKeyboardMarkup(kb)

    message_text = f"{user_mention} wants to hold \"{event_name}\" and is calling for ideas!\n\n"
    message_text += "Help make it a successful event and contribute your ideas!"

    await update.message.reply_html(
        message_text,
        reply_markup=reply_markup
    )

async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide an event name after /schedule.")
        return

    event_name = " ".join(context.args)
    user = update.effective_user
    user_mention = user.mention_html()

    # Construct the combined message
    message = (
        f"{user_mention} is proposing that we have: {event_name}\n\n"
        "Choose an action below:"
    )

    # Create inline keyboard buttons stacked vertically
    keyboard = [
        [InlineKeyboardButton("Share your ideas", url=MINI_APP_URL)],
        [InlineKeyboardButton("Vote for your favorite idea", url=MINI_APP_URL)]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the message with HTML formatting and inline keyboard
    await update.message.reply_text(
        message,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

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

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, event_id = query.data.split('_', 1)
    user_id = update.effective_user.id

    if event_id not in events:
        await query.edit_message_text("This event has expired or doesn't exist.")
        return

    event = events[event_id]
    
    if action == 'vote':
        if user_id not in event['voters']:
            event['vote_count'] += 1
            event['voters'].add(user_id)
    elif action == 'share':
        if user_id not in event['sharers']:
            event['share_count'] += 1
            event['sharers'].add(user_id)

    # Update the message with new counts
    keyboard = [
        [InlineKeyboardButton(f"Vote for your favourite idea! ({event['vote_count']})", callback_data=f"vote_{event_id}")],
        [InlineKeyboardButton(f"Share your idea! ({event['share_count']})", callback_data=f"share_{event_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_reply_markup(reply_markup=reply_markup)

# Sets the bot commands
async def post_init(application: Application) -> None:
    await application.bot.set_my_commands([('start', 'Starts the bot'), ('echo', 'Add some commands after the command'), ('schedule', 'Schedule a meeting')])

async def insert_message(message_text, sender_id):
    data = {
        "id": 'testid',
        "name": 'testevent',
        'description': 'this event is a big deal',
        'userId': 'ryan',
        'chatId': '123'
    }
    response = supabase.table('Event').insert(data).execute()
    if response.status_code == 201:
        print("Data inserted successfully.")
    else:
        print(f"Error inserting data: {response.data}")

async def handle_message(update, context):
    message_text = update.message.text
    sender_id = update.message.from_user.id
    # Trigger insert_message
    await insert_message(message_text, sender_id)
    await update.message.reply_text("Your message has been saved.")



if __name__ == '__main__':
    # Run app builder
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Command Handlers
    message_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    application.add_handler(message_handler)

    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('echo', echo_command))
    application.add_handler(CommandHandler('schedule', schedule_command))
    # application.add_handler(CallbackQueryHandler(button_callback))
    
    # Message Handlers
    application.add_handler(MessageHandler(filters.Text, handle_message))

    # Web App Data Handler
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))   
    # application.add_handler(CallbackQueryHandler(button))
    
    # Run the bot 
    application.run_polling()
    