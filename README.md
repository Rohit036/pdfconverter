# pdfconverter

A Telegram and WhatsApp bot that converts images to PDF files.

## Features

- Send any image (photo or image document) to the bot via **Telegram** or **WhatsApp**
- Receive a PDF version of that image instantly
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
| `TWILIO_ACCOUNT_SID` | Your Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | Your Twilio Auth Token |
| `PUBLIC_BASE_URL` | Public base URL that Twilio can reach, such as your ngrok or Railway URL |
| `PORT` | Port for the FastAPI webhook server (default: `5000`) |
| `TELEGRAM_BOT_TOKEN` | Token from BotFather (only needed for the Telegram bot flow) |
| `TWILIO_WHATSAPP_NUMBER` | Twilio WhatsApp sender (only needed for other Twilio flows in this repo) |

### 4. Run the app

```bash
python whatsapp_pdf_app.py
```

This starts the FastAPI/uvicorn webhook server on the configured port.

---

## Testing WhatsApp + Twilio locally

The Twilio sandbox sends HTTP POST requests to your webhook URL, so your local machine must be reachable from the internet. Use [ngrok](https://ngrok.com/) to create a secure tunnel.

### Step 1 — Install ngrok

Download from <https://ngrok.com/download> or install via npm:

```bash
npm install -g ngrok
```

### Step 2 — Start the app

```bash
python whatsapp_pdf_app.py
# FastAPI server listening on http://0.0.0.0:5000
```

### Step 3 — Expose port 5000 with ngrok

Open a **second terminal** and run:

```bash
ngrok http 5000
```

ngrok will display a public HTTPS URL, for example:

```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:5000
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

- **Text message**: send `hello` → the app replies with a welcome prompt.
- **Other text**: send any text without an image → the app asks you to send an image.
- **Image**: send any JPEG/PNG image → the app converts it and sends back a PDF.

You can watch the live requests in the ngrok terminal and in the bot's log output.

---

## Commands (Telegram)

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/help`  | Usage instructions |

---

## Deploy `whatsapp_pdf_app.py` to Railway

[Railway](https://railway.app) is a cloud platform that lets you deploy the bot in minutes without managing servers.

### Steps

1. **Fork / push this repository** to your own GitHub account.

2. **Create a Railway account** at <https://railway.app> (free tier is available).

3. **Create a new project**:
   - Click **New Project → Deploy from GitHub repo**.
   - Select your forked repository.
   - Railway will auto-detect Python and install dependencies from `requirements.txt`.

4. **Railway start command / Procfile**:
   - This repository is configured to start `whatsapp_pdf_app.py`.
   - Railway uses `python whatsapp_pdf_app.py`, which starts the FastAPI app on `0.0.0.0:$PORT`.

5. **Add environment variables**:
   - In your Railway project, open the **Variables** tab.
   - For `whatsapp_pdf_app.py`, add:

      | Variable | Required | Example | Notes |
      |---|---|---|---|
      | `TWILIO_ACCOUNT_SID` | Yes | `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` | Used to download the image media that Twilio sends to the webhook. |
      | `TWILIO_AUTH_TOKEN` | Yes | `your_auth_token` | Used together with the account SID for Twilio media auth. |
      | `PUBLIC_BASE_URL` | Recommended | `https://your-app.up.railway.app` | Set this explicitly if you want a fixed public URL for the generated PDF links. |
      | `PORT` | Usually automatic | `5000` | Railway normally injects this for you. |

   - If `PUBLIC_BASE_URL` is omitted, `whatsapp_pdf_app.py` will try to use Railway's public domain variables automatically.
   - `TELEGRAM_BOT_TOKEN` and `TWILIO_WHATSAPP_NUMBER` are not required for this app.

6. **Set the Twilio webhook URL** to your Railway deployment URL:

   ```
   https://<your-railway-app>.railway.app/whatsapp
   ```

7. **Verify the deployment**:
    - Open the **Deployments** tab and wait for the build to finish.
    - Check the **Logs** tab — the FastAPI app should start successfully on Railway's assigned port.
    - Open `https://<your-railway-app>.railway.app/` and confirm it returns `{"ok": true}`.
    - Send `hi` or `hello` to your Twilio WhatsApp number and confirm you receive the prompt asking for an image.
    - Send an image and confirm you receive a PDF reply from the webhook.

### Notes

- If the process crashes, Railway will restart it automatically (configured in `railway.json`).
- To update the bot, simply push a new commit to GitHub — Railway will redeploy automatically.
- Generated PDFs are stored on the Railway instance filesystem, so they are intended for short-lived delivery links rather than permanent storage.
