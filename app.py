import os

from anthropic import Anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, Form
from fastapi.responses import Response
from twilio.twiml.voice_response import Gather, VoiceResponse

from prompts import system_prompt
from state import history, reset
from tools import TOOL_DEFS, run_tool

load_dotenv()

MODEL = "claude-haiku-4-5-20251001"
MAX_TOOL_ITERATIONS = 5
GATHER_TIMEOUT = 4
SPEECH_LANGUAGE = "en-US"

app = FastAPI()
claude = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def twiml(resp: VoiceResponse) -> Response:
    return Response(content=str(resp), media_type="application/xml")


def gather(say_text: str, action: str = "/turn") -> VoiceResponse:
    resp = VoiceResponse()
    g = Gather(
        input="speech",
        action=action,
        method="POST",
        speech_timeout="auto",
        timeout=GATHER_TIMEOUT,
        language=SPEECH_LANGUAGE,
    )
    g.say(say_text)
    resp.append(g)
    resp.redirect("/timeout", method="POST")
    return resp


def assistant_turn(call_sid: str, user_text: str) -> str:
    msgs = history(call_sid)
    msgs.append({"role": "user", "content": user_text})

    for _ in range(MAX_TOOL_ITERATIONS):
        reply = claude.messages.create(
            model=MODEL,
            max_tokens=512,
            system=system_prompt(),
            tools=TOOL_DEFS,
            messages=msgs,
        )

        msgs.append({"role": "assistant", "content": reply.content})

        if reply.stop_reason != "tool_use":
            return "".join(b.text for b in reply.content if b.type == "text").strip()

        tool_results = []
        for block in reply.content:
            if block.type != "tool_use":
                continue
            try:
                result = run_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result),
                })
            except Exception as e:
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": f"error: {e}",
                    "is_error": True,
                })
        msgs.append({"role": "user", "content": tool_results})

    return "I'm sorry, I got a bit confused. Could you say that again?"


@app.post("/voice")
async def voice(CallSid: str = Form(...)):
    reset(CallSid)
    greeting = assistant_turn(CallSid, "[The caller has just dialled in. Greet them briefly and ask how you can help.]")
    return twiml(gather(greeting))


@app.post("/turn")
async def turn(CallSid: str = Form(...), SpeechResult: str = Form(default="")):
    if not SpeechResult.strip():
        return twiml(gather("I didn't catch that. Could you say it again?"))
    reply = assistant_turn(CallSid, SpeechResult)
    return twiml(gather(reply))


@app.post("/timeout")
async def timeout(CallSid: str = Form(...)):
    resp = VoiceResponse()
    resp.say("I didn't hear anything. Goodbye, take care.")
    resp.hangup()
    reset(CallSid)
    return twiml(resp)


@app.get("/health")
async def health():
    return {"ok": True}
