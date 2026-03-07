import os
from urllib.parse import parse_qs

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse

load_dotenv()

app = FastAPI()


@app.get("/")
def health():
    return {"ok": True}


@app.post("/whatsapp")
async def whatsapp_webhook(request: Request) -> Response:
    raw_body = (await request.body()).decode()
    data = parse_qs(raw_body)

    incoming_text = data.get("Body", [""])[0].strip()
    sender = data.get("From", [""])[0]

    resp = MessagingResponse()

    if incoming_text.lower() in {"hi", "hello", "hey"}:
        resp.message("Hello from FastAPI. Send any text and I will reply.")
    else:
        resp.message(f"From {sender}: you said '{incoming_text or 'empty message'}'")

    return Response(content=str(resp), media_type="application/xml")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "5000"))
    uvicorn.run("whatsapp_reply_app:app", host="0.0.0.0", port=port, reload=True)