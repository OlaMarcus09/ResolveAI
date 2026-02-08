import os
import asyncio
import uvicorn  # <--- NEW IMPORT
from datetime import datetime
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.request import HTTPXRequest 
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from dotenv import load_dotenv

# Import your modules
from app.bot import start, save_goal, handle_chat, WAITING_FOR_RES
from app.storage import get_all_users
from app.brain import BRAIN_ENGINE

load_dotenv()

# --- CONFIGURATION ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
# Render gives you a PORT variable. We must use it.
PORT = int(os.environ.get("PORT", 10000))

app = FastAPI()
scheduler = AsyncIOScheduler()

# Global variable to hold the bot application
ptb_app = None

async def proactive_cycle(application):
    """Checks for reminders and triggers the proactive AI message."""
    users = get_all_users()
    if not users: return
    
    # Get current time (e.g., "00:00")
    now_str = datetime.now().strftime("%H:%M")
    print(f"⏰ Tick: {now_str} ...")
    
    for chat_id, data in users.items():
        if data.get("phase") != "active":
            continue
            
        user_time = data.get("reminder_time") 
        
        if user_time != now_str:
            continue
            
        print(f"   🔔 Waking up for {data.get('name', chat_id)} (Scheduled: {user_time})")
        
        try:
            # We run the blocking AI engine in a separate thread to not freeze the bot
            result = await asyncio.to_thread(
                BRAIN_ENGINE.invoke, 
                {
                    "chat_id": chat_id, 
                    "is_proactive": True, 
                    "response": None,
                    "phase": "active"
                }
            )
            
            if result.get("response"):
                await application.bot.send_message(chat_id=chat_id, text=f"⚡ {result['response']}")
        except Exception as e:
            print(f"   ❌ Brain Error: {e}")

@app.on_event("startup")
async def startup():
    global ptb_app
    print("🚀 Starting ResolveAI System...")

    # --- THE NETWORK FIX ---
    t_request = HTTPXRequest(connection_pool_size=8, connect_timeout=60, read_timeout=60, write_timeout=60)
    
    # Build the App
    ptb_app = Application.builder().token(TOKEN).request(t_request).build()
    
    # Handlers
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={WAITING_FOR_RES: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_goal)]},
        fallbacks=[]
    )
    ptb_app.add_handler(conv)
    ptb_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_chat))
    
    # Initialize & Start
    await ptb_app.initialize()
    await ptb_app.start()
    
    # Start Polling (Non-blocking)
    asyncio.create_task(ptb_app.updater.start_polling())
    
    # Scheduler
    scheduler.add_job(
        proactive_cycle, 
        'interval', 
        seconds=60, 
        args=[ptb_app],
        misfire_grace_time=120, 
        coalesce=True
    )
    scheduler.start()
    print(f"✅ ResolveAI Online on Port {PORT}")

@app.get("/")
def home():
    return {"status": "Online", "bot": "Running"}

# --- CRITICAL MISSING PIECE ---
if __name__ == "__main__":
    # This tells Render: "Run the app on this specific port!"
    uvicorn.run(app, host="0.0.0.0", port=PORT)