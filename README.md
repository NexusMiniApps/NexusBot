# Production Development

Make changes, push, and it should automatically redeploy.

# Where is the important stuff?
```
NexusBot/
└───── app.py         // code for all major functions of the bot
```

# Local Development (Only for Bot Server side)

1. Go to https://t.me/botfather and create a new bot. Note down the bot token generated.
2. Git clone the repository.
3. Set up poetry:
   - Install pipx following the instructions in the [official doumentation](https://pipx.pypa.io/stable/installation/)
   - Run `pipx install poetry`
4. Install the required packages using `poetry install`.
5. Create a .env file in the root directory and add the following

```bash
BOT_TOKEN='YOUR_BOT_TOKEN'
BOT_URL='https://t.me/[YOUR_BOT_NAME]'
APP_URL="YOUR_NGROK_TUNNEL_URL"
MINI_APP_URL="https://t.me/[YOUR_BOT_NAME]/[YOUR_MINI_APP_NAME]/"

// All of the following can be found on the supabase dashboard
SUPABASE_URL="YOUR_PROJECT_URL"
SUPABASE_KEY="PROJECT_API_KEY"
DATABASE_URL="CONNECTION_STRING(SESSION)"
DIRECT_URL="CONNECTION_STRING(TRANSACTION)"
```

6. Run `poetry shell` in the terminal to start the virtual environment.
7. Run `python app.py` in the shell to start the bot server.

# Local Development (Both Bot Server and Web Server side)

1. Follow the instructions in the previous section to start your own bot server on one terminal.
2. In another terminal, head over to the [web server repository](https://github.com/NexusMiniApps/NexusMeet), `git clone`, `npm i` and `npm run dev` to start the web server on local host.
3. Setup [ngrok tunneling service](https://ngrok.com/docs/getting-started/) to expose the local server to the internet and follow the instructions to also create a static domain.
4. In another terminal, run the command `ngrok http 3000 --domain [your static domain]`. You should now have 3 terminals running. One for the bot server, one for the web server, and one for the ngrok tunneling service.
5. In the .env file of the bot server, add the ngrok URL
   `APP_URL=YOUR_NGROK_URL`
6. You're now done! Any changes made to the bot server wil reflect in the bot. Any changes made to the web server will reflect in the web app.

# Debugging in telegram

1. Follow the instructions [here](https://docs.ton.org/develop/dapps/telegram-apps/testing-apps)

Side Note: I am still unsure of the difference between the bot url and the mini app url. You can register the mini app with botfather but I don't understand what is the point yet.

- BOT_URL='https://t.me/aug23nexus_bot'
- MINI_APP_URL='t.me/aug23nexus_bot/aug23nexusapp'.
