import os
import asyncio
from datetime import datetime
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
# 1. Import the Network Shield
from telegram.request import HTTPXRequest 
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
    # --- THE NETWORK FIX IS HERE ---
    # This tells the bot: "Wait 60 seconds for the internet before crashing."
    t_request = HTTPXRequest(connection_pool_size=8, connect_timeout=60, read_timeout=60, write_timeout=60)
    
    # Build the App using the strong request settings
    ptb = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).request(t_request).build()
    
    # Handlers
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={WAITING_FOR_RES: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_goal)]},
        fallbacks=[]
    )
    ptb.add_handler(conv)
    
    # This line enables the CHAT functionality (Responding to your questions)
    ptb.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_chat))
    
    await ptb.initialize()
    await ptb.start()
    asyncio.create_task(ptb.updater.start_polling())
    
    # Lag-Proof Scheduler
    scheduler.add_job(
        proactive_cycle, 
        'interval', 
        seconds=60, 
        args=[ptb],
        misfire_grace_time=120, 
        coalesce=True
    )
    scheduler.start()
    print("✅ ResolveAI System Online (Strong Connection Mode).")

@app.get("/")
def home(): return {"status": "Online"}