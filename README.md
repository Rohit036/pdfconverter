# pdfconverter

A Telegram and WhatsApp bot that converts images to PDF files.

## Features

- Send any image (photo or image document) to the bot via **Telegram** or **WhatsApp**
- Receive a PDF version of that image instantly
- WhatsApp offers **Single page conversion** and **Multipage conversion** modes
- Supports JPEG, PNG, BMP, GIF, TIFF, WEBP and other common formats
- WhatsApp integration powered by **Twilio** with a **FastAPI** webhook

## Setup

### 1. Create a Telegram bot

1. Open Telegram and start a chat with [@BotFather](https://t.me/BotFather).
2. Send `/newbot` and follow the prompts.
3. Copy the **bot token** you receive.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
# Open .env and fill in your tokens
```

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token from BotFather |
| `TWILIO_ACCOUNT_SID` | Your Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | Your Twilio Auth Token |
| `TWILIO_WHATSAPP_NUMBER` | Twilio WhatsApp sender (e.g. `whatsapp:+14155238886`) |
| `PORT` | Port for the FastAPI webhook server (default: `8000`) |

### 4. Run the bot

```bash
python bot.py
```

This starts both the Telegram polling loop and the FastAPI/uvicorn webhook server on the configured port.

---

## Testing WhatsApp + Twilio locally

The Twilio sandbox sends HTTP POST requests to your webhook URL, so your local machine must be reachable from the internet. Use [ngrok](https://ngrok.com/) to create a secure tunnel.

### Step 1 — Install ngrok

Download from <https://ngrok.com/download> or install via npm:

```bash
npm install -g ngrok
```

### Step 2 — Start the bot

```bash
python bot.py
# FastAPI server listening on http://0.0.0.0:8000
```

### Step 3 — Expose port 8000 with ngrok

Open a **second terminal** and run:

```bash
ngrok http 8000
```

ngrok will display a public HTTPS URL, for example:

```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:8000
```

Copy the `https://` forwarding URL.

### Step 4 — Configure the Twilio WhatsApp sandbox webhook

1. Go to the [Twilio Console](https://console.twilio.com/).
2. Navigate to **Messaging → Try it out → Send a WhatsApp message**.
3. In the **Sandbox settings** tab, set the **"When a message comes in"** field to:

   ```
   https://abc123.ngrok-free.app/whatsapp
   ```

   Make sure the method is **HTTP POST**.
4. Click **Save**.

### Step 5 — Join the sandbox

Follow the on-screen instructions in the Twilio Console to join the sandbox by sending the join code (e.g. `join <sandbox-word>`) from your WhatsApp to the Twilio sandbox number.

### Step 6 — Test it

- **Text message**: send `hello` → bot replies with the two conversion options.
- **Single page**: reply with `1`, then send one or more JPEG/PNG images → bot returns one PDF per image.
- **Multipage**: reply with `2`, then send one or more JPEG/PNG images → bot returns one merged PDF in upload order.

You can watch the live requests in the ngrok terminal and in the bot's log output.

---

## Commands (Telegram)

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/help`  | Usage instructions |

---

## Deploy `whatsapp_reply_app.py` to Railway

[Railway](https://railway.app) is a cloud platform that lets you deploy the bot in minutes without managing servers.

### Steps

1. **Fork / push this repository** to your own GitHub account.

2. **Create a Railway account** at <https://railway.app> (free tier is available).

3. **Create a new project**:
   - Click **New Project → Deploy from GitHub repo**.
   - Select your forked repository.
   - Railway will auto-detect Python and install dependencies from `requirements.txt`.

4. **Railway start command / Procfile**:
   - This repository is configured to start `whatsapp_reply_app.py`.
   - `whatsapp_reply_app.py` now serves the WhatsApp PDF converter flow via the shared FastAPI app.
   - Railway uses `python whatsapp_reply_app.py`, which starts the FastAPI app on `0.0.0.0:$PORT`.

5. **Add environment variables**:
   - In your Railway project, open the **Variables** tab.
   - Add the following values for the WhatsApp PDF converter flow:

      | Variable | Required | Example | Notes |
      |---|---|---|---|
      | `PORT` | Yes | `5000` | Railway usually injects this automatically, but you can add it manually if needed. |
      | `TWILIO_ACCOUNT_SID` | Yes | `AC...` | Used to download incoming media from Twilio securely. |
      | `TWILIO_AUTH_TOKEN` | Yes | `...` | Used with the account SID for media downloads. |
      | `PUBLIC_BASE_URL` | Yes | `https://<your-railway-app>.railway.app` | Used to build public `/files/...` links for PDF replies. |

6. **Set the Twilio webhook URL** to your Railway deployment URL:

   ```
   https://<your-railway-app>.railway.app/whatsapp
   ```

7. **Verify the deployment**:
     - Open the **Deployments** tab and wait for the build to finish.
     - Check the **Logs** tab — the FastAPI app should start successfully on Railway's assigned port.
     - Open `https://<your-railway-app>.railway.app/` and confirm it returns `{"ok": true}`.
     - Send `hi` or `hello` to your Twilio WhatsApp number and confirm you receive the two conversion options.
     - Reply with `1` or `2`, send images, and confirm you receive the expected PDF reply.

### Notes

- If the process crashes, Railway will restart it automatically (configured in `railway.json`).
- To update the bot, simply push a new commit to GitHub — Railway will redeploy automatically.
- `whatsapp_reply_app.py` and `whatsapp_pdf_app.py` now share the same WhatsApp PDF conversion flow.
