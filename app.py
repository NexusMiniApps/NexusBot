from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Updater, CallbackContext, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ApplicationBuilder
from urllib.parse import urljoin
import json
import logging
import os
import threading
from supabase import create_client, Client
import uuid
import time
from datetime import datetime

if os.path.exists(".env"):
    # if we see the .env file, load it
    from dotenv import load_dotenv
    load_dotenv()

# Telegram Bot setup
BOT_TOKEN = os.getenv('BOT_TOKEN')
MINI_APP_URL = os.getenv('MINI_APP_URL')
BOT_URL = os.getenv('BOT_URL', 'https://t.me/NexusMiniApps_Bot/NexusMeet')
APP_URL = os.getenv('APP_URL', "https://nexusmeet.vercel.app/new-meeting")

# Supabase setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Defaults to local dev environment
ENDPOINT = os.getenv("DEV_URL")
if ENDPOINT is None:
    ENDPOINT = os.getenv('LIVE_URL')
VOTE_ENDPOINT = os.getenv("VOTE_ENDPOINT")
SHARE_ENDPOINT = os.getenv("SHARE_ENDPOINT")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# If user exists, retrieve pk, if not create user then retrieve pk
def retrieve_user_key(user):
    response = supabase.table('User').select('*').eq('telegramId', user.id).execute()
    if len(response.data) > 0:
        print("User exists")
        return response.data[0]['id']
    else:
        print("User doesn't exist")
        response = supabase.table('User').insert({'telegramId': user.id, 'username': user.username, 'firstName': user.first_name, 'lastName': user.last_name}).execute()
        return response.data[0]['id']

def test_function(update: Update, context: CallbackContext):
    print('testing')
    userId = retrieve_user_key(update.effective_user)
    print(userId)

def start_command(update: Update, context: CallbackContext):
    kb = [
        [InlineKeyboardButton("Create a meeting!", web_app=WebAppInfo(APP_URL))]
    ]

    update.message.reply_text("Welcome to NexusMeet!", reply_markup=InlineKeyboardMarkup(kb))

# Handles the /confirm command to confirm an event
async def confirm_command(update: Update, context: CallbackContext):
    print("Confirm command triggered")
    try:
        # Fetch event name and chat id from the message
        if context.args:
            event_name = " ".join(context.args)
        else:
            await update.message.reply_text("Please provide the event name.")
            return

        chat_id = update.effective_chat.id
        print(f"Event: {event_name}, Chat ID: {chat_id}")
        # Query Supabase for the event and chat_id
        data = supabase.table('Event').select('*').eq('name', event_name).eq('chatId', chat_id).eq('status', "PENDING").execute()

        # Check if the event exists
        if len(data.data) > 0:
            # Construct the mini-app URL to open the to_confirm form and idea viewer
            app_url = f"http://localhost:3000/eventId"

            # Open the mini-app by sending a message with an inline button
            keyboard = [[InlineKeyboardButton("Open Mini-App", url=app_url)]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text("Event confirmed! Open the mini-app:", reply_markup=reply_markup)
        else:
            await update.message.reply_text("No such event found for this chat.")

    except Exception as e:
        await update.message.reply_text(f"An error occurred: {e}")

# Function to handle event confirmation from the web app
async def handle_event_confirmation(bot, event_name, event_id, chat_id, user_id, topic_id):
    # Create inline buttons
    keyboard = [
        [InlineKeyboardButton("Yes", callback_data=f"upvote_{event_id}"),
         InlineKeyboardButton("No", callback_data=f"downvote_{event_id}"),
         InlineKeyboardButton("Maybe", callback_data=f"questionmark_{event_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send message to the group chat
    print(f"Sending confirmation message for event {event_name} to chat {chat_id}...")  # Debugging line

    # Send message to the group chat
    try:
        message = await bot.send_message(
            chat_id=chat_id,
            message_thread_id = topic_id,
            text=f"The {event_name} is confirmed! Let us know if you're coming!",
            reply_markup=reply_markup
        )
        # Store message_id and chat_id associated with the event
        store_event_message(event_id, chat_id, message.message_id)

    except Exception as e:
        print(f"Failed to send message: {e}")

# Handles the button clicks for RSVP
async def rsvp_button_click_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer(text="Thanks for your response!", show_alert=False)

    # Extract event name and action (upvote/downvote) from callback_data
    action, event_id = query.data.split("_")
    chat_id = update.effective_chat.id
    message_id = query.message.message_id

    # Fetch user_uuid from Supabase:
    user_uuid = retrieve_user_key(update.effective_user)
    username = update.effective_user.username

    # Map action to status
    status_mapping = {
        "upvote": "YES",
        "downvote": "NO",
        "questionmark": "MAYBE"
    }
    status = status_mapping.get(action)

    # Update the user's response in Supabase
    update_supabase_event_vote(event_id, user_uuid, chat_id, status)

    # Update the original message to show responses
    await update_event_message(context.bot, event_id, chat_id, message_id)

async def update_event_message(bot, event_id, chat_id, message_id):
    # Fetch event details
    event = get_event_by_id(event_id)
    event_name = event.get('name', 'Event')

    # Fetch all responses for this event
    responses = get_event_responses(event_id)  # Implement this function

    # Organize responses by status
    response_counts = {'YES': [], 'NO': [], 'MAYBE': []}
    for response in responses:
        resp_status = response['status']
        user_id = response['userId']
        user_info = get_user_info(user_id)  # Implement this function
        user_name = user_info.get('username') or user_info.get('firstName')
        response_counts[resp_status].append(user_name)

    # Build the updated message text
    response_text = f"The {event_name} is confirmed! Let us know if you're coming!\n\n"
    for status, users in response_counts.items():
        user_list = ', '.join(users) if users else 'No responses yet'
        response_text += f"{status.title()} ({len(users)}): {user_list}\n"

    # Reconstruct the inline keyboard
    keyboard = [
        [InlineKeyboardButton("Yes", callback_data=f"upvote_{event_id}"),
         InlineKeyboardButton("No", callback_data=f"downvote_{event_id}"),
         InlineKeyboardButton("Maybe", callback_data=f"questionmark_{event_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Edit the original message
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=response_text,
            reply_markup=reply_markup
        )
    except Exception as e:
        print(f"Failed to edit message: {e}")

def update_supabase_event_vote(event_id, user_id, chat_id, status):
    # Define the status based on the upvote
    status = status.upper()  # Expecting 'YES', 'NO', or 'MAYBE'

    # Check if the user has already voted
    response = supabase.from_("EventRSVPs").select("*").eq("eventId", event_id).eq("userId", user_id).execute()

    if response.data and len(response.data) > 0:
        # User has already voted, so update the existing vote
        vote_id = response.data[0]['id']
        supabase.from_("EventRSVPs").update({"status": status}).eq("id", vote_id).execute()
        print(f"Updated existing vote for user {user_id} with status {status}")
    else:
        # User has not voted yet, insert a new row with the status
        supabase.from_("EventRSVPs").insert({
            "eventId": event_id,
            "userId": user_id,
            "chatId": chat_id,
            "status": status
        }).execute()
        print(f"Inserted new vote for user {user_id} with status {status}")

def get_user_info(user_id):
    response = supabase.from_("User").select("*").eq("id", user_id).single().execute()
    return response.data or {}

def get_event_responses(event_id):
    response = supabase.from_("EventRSVPs").select("*").eq("eventId", event_id).execute()
    return response.data or []

def get_event_by_id(event_id):
    # Query the 'Event' table for the event with the specified event_id
    response = supabase.from_("Event").select("*").eq("id", event_id).single().execute()

    # Check if the response was successful and data is returned
    if response.data:
        return response.data
    else:
        # Handle the case where the event is not found
        print(f"No event found with id {event_id}")
        return None

def store_event_message(event_id, chat_id, message_id):
    # Store message_id and chat_id in your database associated with the event_id
    supabase.from_("Event").update({
        "messageId": message_id,
        "chatId": chat_id
    }).eq("id", event_id).execute()

async def schedule_command(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("Please provide an event name after /schedule.")
        return

    event_name = " ".join(context.args)
    user = update.effective_user

    user_mention = user.mention_html()
    chat_id = update.effective_chat.id
    topic_id = update.effective_message.message_thread_id
    

    # Insert the user into the Supabase DB if it doesn't exist:
    user_uuid = retrieve_user_key(user)

    # Insert the event into the Supabase DB:
    data = {
        "name": event_name,
        "description": "",
        "chatId": chat_id,
        "userId": user_uuid,
        "status": "PENDING",
        "topicId": topic_id,
    }

    try:
        response = supabase.table('Event').insert(data).execute()
        print(data)
        if response.data:
            # Assuming 'id' is the UUID column in the 'Event' table
            generated_uuid = response.data[0]['id']
            print(f"Data inserted successfully. Generated Event UUID: {generated_uuid}")
        else:
            print("No data returned from Supabase.")

    except Exception as e:
        return

    # Construct the combined message
    message = (
        f"{user_mention} is proposing that we have: {event_name}\n\n"
        "Choose an action below:"
    )

    print(MINI_APP_URL + f"?startapp={generated_uuid}/newidea")
    
    keyboard = [
        [InlineKeyboardButton("Share your ideas", url=MINI_APP_URL + f"?startapp={generated_uuid}newidea" + "&mode=compact")],
        [InlineKeyboardButton("Vote for your favorite idea", url=MINI_APP_URL + f"?startapp={generated_uuid}" + "&mode=compact")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the message with HTML formatting and inline keyboard
    await update.message.reply_text(
        message,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

def test_rsvp_command(update: Update, context: CallbackContext):
    handle_event_confirmation(context.bot, event_name="Prisoner's Dilemma 8", event_id="745d4de3-71fd-4637-a3a4-fe2355ea27db", chat_id=update.effective_chat.id, user_id=update.effective_user.id)

def handle_message(update: Update, context: CallbackContext):
    text = str(update.message.text).lower()
    update.message.reply_text(f"Your message was: {text}")

def web_app_data(update: Update, context: CallbackContext):
    data = json.loads(update.message.web_app_data.data)
    update.message.reply_text("Your data was:")
    update.message.reply_text(data)

# Sets the bot commands
def post_init(application) -> None:
    bot = application.bot
    bot.set_my_commands([('start', 'Starts the bot'), ('schedule', 'Schedule a meeting')])

def supabase_listener(bot):
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def listener():
        while True:
            try:
                response = supabase.table('Event').select('*').eq('status', 'CONFIRMED').eq('rsvpSent', False).execute()
                events = response.data or []
                for event in events:
                    event_id = event['id']
                    # Handle the event
                    event_name = event['name']
                    chat_id = event['chatId']
                    user_id = event['userId']
                    topic_id = event.get('topicId')
                    # Handle event confirmation
                    await handle_event_confirmation(bot, event_name, event_id, chat_id, user_id, topic_id)
                    # Update the Event record to mark RSVPSent as True
                    supabase.table('Event').update({'rsvpSent': True}).eq('id', event_id).execute()
                # Sleep for some time
                await asyncio.sleep(5)
            except Exception as e:
                print(f"Error in supabase_listener: {e}")
                await asyncio.sleep(5)

    loop.run_until_complete(listener())



def main():
    global app
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Command Handlers
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('schedule', schedule_command))
    app.add_handler(CommandHandler('confirm', confirm_command))
    app.add_handler(CommandHandler('test', test_function))
    app.add_handler(CommandHandler('test_rsvp', test_rsvp_command))

    # Web App Data Handler
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    app.add_handler(CallbackQueryHandler(rsvp_button_click_handler))

    # Start the Supabase listener as a background thread
    bot = app.bot
    supabase_thread = threading.Thread(target=supabase_listener, args=(bot,), daemon=True)
    supabase_thread.start()

    print("Bot started.")

    app.run_polling()

    # Once the bot stops, the thread will exit because it's a daemon thread
    print("Bot stopped.")

if __name__ == '__main__':
    main()
