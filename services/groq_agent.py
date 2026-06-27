import json
import re
from groq import Groq

import config
from services import mcp_client

_groq_client: Groq | None = None

SYSTEM_PROMPT = """You are MedBridge AI, a multilingual healthcare assistant for India.
Help patients find doctors, understand symptoms, and book appointments.
Also assist doctors and nurses with patient-related queries.

RULES:
1. Detect user language from their message. Always respond in that
   SAME language. Supported: English, Hindi (हिन्दी), Tamil (தமிழ்),
   Telugu (తెలుగు), Kannada (ಕನ್ನಡ), Malayalam (മലയാളം),
   Bengali (বাংলা), Marathi (मराठी), Gujarati (ગુજરાતી).
2. NEVER give a definitive diagnosis. Say symptoms "may suggest"
   a condition and always recommend seeing a doctor.
3. When a patient describes symptoms, call search_doctors to find
   nearby specialists. Ask for location if not already provided.
4. When returning doctor results, format them inside this exact tag:
   <DOCTOR_CARDS>[{...json array...}]</DOCTOR_CARDS>
   Each object: { doctor_id, name, specialization, distance_km,
   rating, languages_spoken, consultation_fee, clinic_name }
5. Before booking, confirm doctor, date, time, and symptoms with user.
6. If patient says urgent -> set is_urgent: true in book_appointment.
7. For doctors/nurses, only share patient data they are authorized for.
8. Be warm, empathetic, and clear.
"""

DOCTOR_CARDS_RE = re.compile(r"<DOCTOR_CARDS>(.*?)</DOCTOR_CARDS>", re.DOTALL)

sessions: dict[str, list[dict]] = {}
MAX_HISTORY = 20


def get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=config.GROQ_API_KEY)
    return _groq_client


def _mcp_schema_to_groq_tools(mcp_tools: list) -> list:
    tools = []
    for t in mcp_tools:
        name = t.get("name") or t.get("tool_name")
        if not name:
            continue
        tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": t.get("description", f"Call the {name} MCP tool."),
                "parameters": t.get("input_schema") or t.get("parameters") or {
                    "type": "object", "properties": {}, "additionalProperties": True
                },
            },
        })
    return tools


def init_session(session_id: str, user_role: str, user_id: str, lat, lng):
    if session_id in sessions:
        return
    context_line = f"User role: {user_role}. User ID: {user_id}."
    if lat is not None and lng is not None:
        context_line += f" Location: lat={lat}, lng={lng}."
    sessions[session_id] = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + context_line},
    ]


def _trim_history(session_id: str):
    history = sessions[session_id]
    if len(history) > MAX_HISTORY + 1:
        sessions[session_id] = [history[0]] + history[-MAX_HISTORY:]


def _chunk_text(text: str, size: int = 6):
    words = text.split(" ")
    buf = []
    for w in words:
        buf.append(w)
        if len(buf) >= size:
            yield " ".join(buf) + " "
            buf = []
    if buf:
        yield " ".join(buf)


async def run_agent_turn(session_id: str, user_message: str, mcp_tools_schema: list, send_json, send_token):
    """One full agent turn: tool-calling loop + streamed final answer.

    send_json(dict)  -> coroutine that sends a JSON control message over the websocket
    send_token(str)  -> coroutine that sends a raw text token/chunk over the websocket
    """
    history = sessions[session_id]
    history.append({"role": "user", "content": user_message})

    elapsed = await mcp_client.ping_mcp()
    if elapsed > config.MCP_SLOW_THRESHOLD_SECONDS:
        await send_json({"type": "mcp_waking"})

    client = get_groq_client()
    tools = _mcp_schema_to_groq_tools(mcp_tools_schema)

    final_text = ""
    for _ in range(5):
        completion = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=history,
            tools=tools if tools else None,
            tool_choice="auto" if tools else None,
        )
        choice = completion.choices[0]
        msg = choice.message

        if msg.tool_calls:
            history.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in msg.tool_calls
                ],
            })
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                try:
                    result = await mcp_client.call_tool(tc.function.name, args)
                except Exception as e:
                    result = {"error": str(e)}
                history.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result),
                })
            continue
        else:
            final_text = msg.content or ""
            history.append({"role": "assistant", "content": final_text})
            break

    _trim_history(session_id)

    doctor_cards = None
    m = DOCTOR_CARDS_RE.search(final_text)
    if m:
        try:
            doctor_cards = json.loads(m.group(1))
        except json.JSONDecodeError:
            doctor_cards = None
        final_text = DOCTOR_CARDS_RE.sub("", final_text).strip()

    if doctor_cards:
        await send_json({"type": "doctor_cards", "data": doctor_cards})

    for chunk in _chunk_text(final_text):
        await send_token(chunk)

    await send_json({"type": "done"})
