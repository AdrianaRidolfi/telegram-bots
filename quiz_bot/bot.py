from fastapi import FastAPI, Request, HTTPException
from fastapi import Depends
from fastapi.responses import JSONResponse
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
)
from contextlib import asynccontextmanager

from config import TOKEN
from handlers import start, handle_callback

application = ApplicationBuilder().token(TOKEN).build()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    await application.initialize()
    print("Bot avviato correttamente.")
    yield
    # Shutdown
    await application.shutdown()
    print("Bot fermato.")

app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
    except Exception as e:
        print(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("bot:app", host="0.0.0.0", port=8000)
