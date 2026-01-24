import os
import asyncio
from datetime import datetime
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from dotenv import load_dotenv

from app.bot import start, save_goal, handle_chat, WAITING_FOR_RES
from app.storage import get_all_users
from app.brain import BRAIN_ENGINE

load_dotenv()
app = FastAPI()
scheduler = AsyncIOScheduler()

async def proactive_cycle(ptb_app):
    users = get_all_users()
    if not users: return
    
    # Get current time (e.g., "00:00")
    now_str = datetime.now().strftime("%H:%M")
    print(f"⏰ Tick: {now_str} ...")
    
    for chat_id, data in users.items():
        # 1. Skip if not active
        if data.get("phase") != "active":
            continue
            
        # 2. Check if the saved time matches NOW
        user_time = data.get("reminder_time") 
        
        if user_time != now_str:
            # Silent
            continue
            
        print(f"   🔔 Waking up for {data['name']} (Scheduled: {user_time})")
        
        # 3. Only invoke Brain if time matches
        try:
            result = BRAIN_ENGINE.invoke({
                "chat_id": chat_id, 
                "is_proactive": True, 
                "response": None,
                "phase": "active"
            })
            
            if result.get("response"):
                await ptb_app.bot.send_message(chat_id=chat_id, text=f"⚡ {result['response']}")
        except Exception as e:
            print(f"   ❌ Brain Error: {e}")

@app.on_event("startup")
async def startup():
    ptb = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()
    
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={WAITING_FOR_RES: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_goal)]},
        fallbacks=[]
    )
    ptb.add_handler(conv)
    ptb.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_chat))
    
    await ptb.initialize()
    await ptb.start()
    asyncio.create_task(ptb.updater.start_polling())
    
    # --- LAG PROTECTION ADDED HERE ---
    scheduler.add_job(
        proactive_cycle, 
        'interval', 
        seconds=60, 
        args=[ptb],
        misfire_grace_time=120,  # Allow up to 2 minutes of delay
        coalesce=True            # If missed multiple times, run just once
    )
    scheduler.start()
    print("✅ ResolveAI Time-Aware System Online (Lag-Proof).")

@app.get("/")
def home(): return {"status": "Online"}