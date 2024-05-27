import os

if os.path.exists(".env"):
    # if we see the .env file, load it
    from dotenv import load_dotenv
    load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
BOT_USERNAME = os.getenv('BOT_USERNAME')