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