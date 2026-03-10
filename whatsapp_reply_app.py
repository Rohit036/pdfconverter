from whatsapp_pdf_app import PORT, app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("whatsapp_reply_app:app", host="0.0.0.0", port=PORT, reload=True)
