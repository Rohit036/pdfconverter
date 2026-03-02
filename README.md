# pdfconverter

A simple Telegram bot that converts images to PDF files.

## Features

- Send any image (photo or image document) to the bot
- Receive a PDF version of that image instantly
- Supports JPEG, PNG, BMP, GIF, TIFF, WEBP and other common formats

## Setup

### 1. Create a Telegram bot

1. Open Telegram and start a chat with [@BotFather](https://t.me/BotFather).
2. Send `/newbot` and follow the prompts.
3. Copy the **bot token** you receive.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure the bot token

```bash
cp .env.example .env
# Open .env and replace "your_bot_token_here" with your actual token
```

### 4. Run the bot

```bash
python bot.py
```

## Usage

1. Open Telegram and search for your bot by the username you set with BotFather.
2. Send `/start` or just send an image.
3. The bot will reply with a PDF file of your image.

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/help`  | Usage instructions |

---

## Deploy to Railway

[Railway](https://railway.app) is a cloud platform that lets you deploy the bot in minutes without managing servers.

### Steps

1. **Fork / push this repository** to your own GitHub account.

2. **Create a Railway account** at <https://railway.app> (free tier is available).

3. **Create a new project**:
   - Click **New Project → Deploy from GitHub repo**.
   - Select your forked repository.
   - Railway will auto-detect Python and install dependencies from `requirements.txt`.

4. **Add the bot token as an environment variable**:
   - In your Railway project, open the **Variables** tab (or click on your service → **Variables**).
   - Click **New Variable** and add:
     - **Name**: `TELEGRAM_BOT_TOKEN`
     - **Value**: the token you copied from BotFather (e.g. `123456:ABC-DEF1234...`)
   - Click **Add** to save. Railway will automatically redeploy with the new variable.

5. **Verify the deployment**:
   - Open the **Deployments** tab and wait for the build to finish (usually under a minute).
   - Check the **Logs** tab — you should see `Bot is running.`
   - Send `/start` to your bot in Telegram to confirm it is responding.

### Notes

- The bot runs as a **worker** process (no HTTP port needed), which is why there is no web server.
- If the process crashes, Railway will restart it automatically (configured in `railway.json`).
- To update the bot, simply push a new commit to GitHub — Railway will redeploy automatically.