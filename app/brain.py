import os
from typing import TypedDict
from google import genai
from opik import track, Opik
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv
from app.storage import get_user, save_user
import re # Added for regex parsing

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
opik_client = Opik(project_name="ResolveAI")

class AgentState(TypedDict):
    chat_id: int
    user_input: str
    is_proactive: bool
    response: str
    phase: str

@track(name="brain_coach")
def coach_node(state: AgentState):
    user = get_user(state["chat_id"])
    
    # --- SCENARIO A: PROACTIVE (Heartbeat) ---
    if state["is_proactive"]:
        prompt = (f"User's Goal: '{user['resolution']}'. It is strictly time to work.\n"
                  "Draft a 1-sentence high-energy command to start working.\n"
                  "Rules: No hello. No questions. Just action.\n"
                  "Formatting: PLAIN TEXT ONLY. Do NOT use asterisks (**) or bolding.")
        response = client.models.generate_content(model="gemini-3-pro-preview", contents=prompt)
        return {"response": response.text}

    # --- SCENARIO B: PLANNING (Intake) ---
    if user.get("phase") == "intake":
        prompt = (
            f"You are a Habit Strategist. User Goal: '{user['resolution']}'.\n"
            f"History: '{state['user_input']}'.\n"
            "Goal: Lock a specific schedule.\n"
            "CRITICAL RULES:\n"
            "1. If the user agrees to a plan, you MUST output a hidden tag at the end: 'ALARM: HH:MM' (24-hour format).\n"
            "2. Example: If user says '12am', output 'ALARM: 00:00'. If '2pm', output 'ALARM: 14:00'.\n"
            "3. Start the final confirmation message with 'PLAN_LOCKED:'\n"
            "4. FORMATTING: Use clean, plain text only. Do NOT use asterisks (**) or markdown bolding."
        )
    else:
        # --- SCENARIO C: ACTIVE (Answering Questions) ---
        prompt = (f"User Goal: {user['resolution']}. User Input: '{state['user_input']}'.\n"
                  "Provide technical advice in clean plain text.\n"
                  "Do NOT use asterisks (**) or bolding. Use simple numbering (1. 2. 3.) if needed.")

    response = client.models.generate_content(model="gemini-3-pro-preview", contents=prompt)
    output = response.text

    # --- PARSING LOGIC ---
    if "ALARM:" in output:
        try:
            # Extract time (e.g., "ALARM: 00:00")
            time_match = re.search(r"ALARM:\s*(\d{2}:\d{2})", output)
            if time_match:
                final_time = time_match.group(1)
                
                # Save to DB (Now works because you fixed storage.py!)
                save_user(state["chat_id"], user['name'], user['resolution'], 
                          plan="Locked", phase="active", reminder_time=final_time)
                
                # Clean up the output (remove the hidden tag)
                output = output.replace(f"ALARM: {final_time}", "").strip()
                # Clean up PLAN_LOCKED tag if visible
                output = output.replace("PLAN_LOCKED:", "").strip()
                
                output += f"\n\n(⏰ System set to remind you daily at {final_time})"
        except Exception as e:
            print(f"Time Parsing Error: {e}")

    # Final cleanup just in case AI slipped an asterisk in
    output = output.replace("**", "")
    
    return {"response": output}

workflow = StateGraph(AgentState)
workflow.add_node("coach", coach_node)
workflow.set_entry_point("coach")
workflow.add_edge("coach", END)
BRAIN_ENGINE = workflow.compile()