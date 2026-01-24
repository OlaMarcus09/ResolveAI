from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from app.storage import save_user, get_user
from app.brain import BRAIN_ENGINE

WAITING_FOR_RES = 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 I am ResolveAI. <b>What is your Resolution?</b>", parse_mode="HTML")
    return WAITING_FOR_RES

async def save_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Save with phase="intake" to start the interview process
    save_user(update.effective_chat.id, update.effective_user.first_name, update.message.text, phase="intake")
    await update.message.reply_text("✅ <b>Goal Locked.</b> Let's build a plan to achieve this.", parse_mode="HTML")
    
    # Trigger the first interview question immediately
    result = BRAIN_ENGINE.invoke({
        "chat_id": update.effective_chat.id, 
        "user_input": "I just set my goal.", 
        "is_proactive": False,
        "response": None,
        "phase": "intake"
    })
    await update.message.reply_text(result["response"])
    return ConversationHandler.END

async def handle_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not get_user(chat_id):
        await update.message.reply_text("Type /start first!")
        return

    # Call the Brain
    result = BRAIN_ENGINE.invoke({
        "chat_id": chat_id, 
        "user_input": update.message.text, 
        "is_proactive": False,
        "response": None,
        "phase": "active" # The brain will check the DB to see the real phase
    })
    
    await update.message.reply_text(result["response"])