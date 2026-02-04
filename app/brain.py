import os
import re
from typing import TypedDict
from google import genai
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv
from app.storage import get_user, save_user

load_dotenv()

# --- CONFIGURATION ---
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# 🚀 HYBRID STRATEGY:
# 1. We try 'gemini-1.5-flash' first because it is instant (0.5s).
# 2. If your key rejects it, we automatically swap to 'gemini-3-pro-preview'.
def generate_safe(prompt_text):
    try:
        # Try the fast model first
        response = client.models.generate_content(
            model="gemini-1.5-flash", 
            contents=prompt_text
        )
        return response.text
    except Exception:
        # 🛡️ FALLBACK: If Flash fails, use the one you KNOW works
        print("⚠️ Flash failed. Switching to Gemini 3 Preview...")
        try:
            response = client.models.generate_content(
                model="gemini-3-pro-preview", 
                contents=prompt_text
            )
            return response.text
        except Exception as e:
            return f"⚠️ SYSTEM ERROR: {str(e)}"

class AgentState(TypedDict):
    chat_id: int
    user_input: str
    is_proactive: bool
    response: str
    phase: str

def coach_node(state: AgentState):
    user = get_user(state["chat_id"])
    
    # --- SCENARIO A: PROACTIVE ---
    if state["is_proactive"]:
        prompt = (f"User's Goal: '{user['resolution']}'. It is strictly time to work.\n"
                  "Draft a 1-sentence high-energy command to start working.\n"
                  "Rules: No hello. No questions. Just action.\n"
                  "Formatting: PLAIN TEXT ONLY.")
        return {"response": generate_safe(prompt)}

    # --- SCENARIO B: PLANNING (Intake) ---
    if user.get("phase") == "intake":
        prompt = (
            f"You are a Habit Strategist. \n"
            f"Current User Resolution in DB: '{user['resolution']}'\n"
            f"User just said: '{state['user_input']}'\n\n"
            "YOUR JOB: Secure a concrete habit loop (Goal + Time).\n\n"
            "LOGIC FLOW (Follow Strictly):\n"
            "1. CHECK GOAL: Is the resolution vague (like 'I want to start')? If yes, ask: 'What specific habit do you want to build?'\n"
            "2. CHECK TIME: If the user hasn't stated a time yet, ask: 'What time of day should we schedule this?'\n"
            "3. CHECK CONFIRMATION: If User says 'Yes'/'Okay' to a proposed time -> YOU MUST LOCK IT.\n"
            "4. LOCKING FORMAT: When locking, output a hidden tag at the very end: 'ALARM: HH:MM' (24-hour).\n\n"
            "Example Interaction:\n"
            "User: 'Read books'\n"
            "AI: 'Great. What time?'\n"
            "User: '9pm'\n"
            "AI: 'Locking reading for 9pm. Correct?'\n"
            "User: 'Yes'\n"
            "AI: 'Plan set. ALARM: 21:00'"
        )
    else:
        # --- SCENARIO C: ACTIVE ---
        prompt = (f"User Goal: {user['resolution']}. User Input: '{state['user_input']}'.\n"
                  "Provide technical advice in clean plain text. Keep it short (max 2 sentences).")

    # Generate Response using the Fail-Safe Function
    output = generate_safe(prompt)

    # --- PARSING LOGIC ---
    if "ALARM:" in output:
        try:
            time_match = re.search(r"ALARM:\s*(\d{1,2}:\d{2})", output)
            if time_match:
                final_time = time_match.group(1)
                if len(final_time) == 4: final_time = "0" + final_time 
                
                save_user(state["chat_id"], user['name'], user['resolution'], 
                          plan="Locked", phase="active", reminder_time=final_time)
                
                output = output.replace(f"ALARM: {final_time}", "").strip()
                output = output.replace(f"ALARM: {time_match.group(1)}", "").strip()
                
                output += f"\n\n(✅ System set to remind you daily at {final_time})"
        except Exception as e:
            print(f"Time Parsing Error: {e}")

    output = output.replace("**", "")
    return {"response": output}

workflow = StateGraph(AgentState)
workflow.add_node("coach", coach_node)
workflow.set_entry_point("coach")
workflow.add_edge("coach", END)
BRAIN_ENGINE = workflow.compile()