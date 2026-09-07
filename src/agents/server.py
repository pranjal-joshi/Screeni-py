"""
OpenAI-compatible /v1 server for issue #301.

- POST /v1/chat/completions  -> chat-complete answer via ScreenipyEngine
- GET  /v1/models             -> static model list
- GET  /health                -> liveness probe (does not require LLM key)

The chat endpoint honors the Skill routing + freshness UX contract.
LLM BYOK is optional: if an API key is configured the engine may call the
LLM; otherwise it directly executes the skill tool chain so contract tests stay
hermetic.
"""
import time
import uuid
import re
from typing import List, Optional, Dict, Any

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field
    _FASTAPI_AVAILABLE = True
except Exception:
    FastAPI = None  # type: ignore
    BaseModel = object  # type: ignore
    _FASTAPI_AVAILABLE = False

from agents.engine import ScreenipyEngine
from agents.byok import load_byok, save_byok, is_configured, byok_path, redacted
from agents.presets import MODEL_PRESETS, DEFAULT_STRATEGY_PACK

_engine: ScreenipyEngine | None = None

def get_engine() -> ScreenipyEngine:
    global _engine
    if _engine is None:
        _engine = ScreenipyEngine()
    return _engine

def reset_engine():
    global _engine
    _engine = None

# ---- Pydantic models (only defined if fastapi available) ----
if _FASTAPI_AVAILABLE:
    class ChatMessage(BaseModel):
        role: str
        content: str

    class ChatCompletionRequest(BaseModel):
        model: str = Field(default="screenipy")
        messages: List[ChatMessage]
        temperature: Optional[float] = None
        max_tokens: Optional[int] = None
        stream: Optional[bool] = False

    class ChatCompletionChoiceMessage(BaseModel):
        role: str
        content: str

    class ChatCompletionChoice(BaseModel):
        index: int
        message: ChatCompletionChoiceMessage
        finish_reason: str

    class ChatCompletionUsage(BaseModel):
        prompt_tokens: int = 0
        completion_tokens: int = 0
        total_tokens: int = 0

    class ChatCompletionResponse(BaseModel):
        id: str
        object: str = "chat.completion"
        created: int
        model: str
        choices: List[ChatCompletionChoice]
        usage: ChatCompletionUsage

def _extract_index_from_messages(messages: List[dict]) -> str:
    """If any message mentions a known index, use it; else default."""
    text = " ".join(m.get("content","") for m in messages).lower()
    # simple index keyword scan
    for idx in ["nifty 50", "nifty 500", "nifty 100", "nifty 200", "nifty smallcap", "nifty midcap", "s&p 500"]:
        if idx in text:
            return idx.title() if "s&p" not in idx else "S&P 500"
    # numeric
    m = re.search(r"nifty\s*500", text)
    if m:
        return "Nifty 500"
    return "Nifty 500"

def _extract_explicit_skill_from_messages(messages: List[dict]) -> Optional[str]:
    text = " ".join(m.get("content","") for m in messages).lower()
    # explicit override patterns
    m = re.search(r"(?:use|run)\s+(breakout|vcp)\b", text)
    if m:
        return m.group(1)
    m = re.search(r"skill:\s*(breakout|vcp)\b", text)
    if m:
        return m.group(1)
    return None

def _last_user_message(messages) -> str:
    for m in reversed(messages):
        role = m.get("role") if isinstance(m, dict) else getattr(m, "role", "")
        content = m.get("content") if isinstance(m, dict) else getattr(m, "content", "")
        if role == "user":
            return content or ""
    # fallback to last message content
    if messages:
        last = messages[-1]
        return last.get("content") if isinstance(last, dict) else getattr(last, "content", "")
    return ""

def _detect_freshness_choice(messages) -> Optional[str]:
    """If the most recent user message is exactly 'fresh'/'stale' after a stale block, treat as HITL choice."""
    last = _last_user_message(messages).strip().lower()
    if last in ("fresh", "stale"):
        return last
    return None

def _build_chat_response(model: str, content: str) -> dict:
    now = int(time.time())
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": now,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }

def create_app(engine: ScreenipyEngine | None = None):
    if not _FASTAPI_AVAILABLE:
        raise ImportError("fastapi is required for the /v1 server (pip install fastapi)")
    from fastapi import FastAPI

    app = FastAPI(title="Screenipy Engine — /v1", version="301")

    _eng = engine or get_engine()

    @app.get("/health")
    def health():
        return {"status": "ok", "engine": "screenipy", "skills": list(_eng.skills.keys()), "byok": is_configured()}

    @app.get("/setup")
    def setup_get():
        # Minimal HTML form - chat-visible error handling done via POST response
        from fastapi.responses import HTMLResponse
        configured = is_configured()
        banner = "<p style='color:green'>BYOK already configured. Submit again to overwrite.</p>" if configured else "<p>First run: set your model key + endpoint. Stored in <code>screenipy_data/byok.json</code>.</p>"
        html = f"""<!doctype html><html><head><meta charset='utf-8'><title>Screenipy Setup</title></head>
<body style='font-family:sans-serif;max-width:640px;margin:2rem auto'>
<h1>Screenipy — First-run setup</h1>
{banner}
<form method='post' action='/setup'>
<label>Provider<br><select name='provider'><option>openai</option><option>openai-compatible</option><option>anthropic</option></select></label><br><br>
<label>API key<br><input name='api_key' type='password' style='width:100%' required></label><br><br>
<label>Base URL (optional, for openai-compatible)<br><input name='base_url' type='text' style='width:100%' placeholder='https://api.openai.com/v1'></label><br><br>
<label>Model<br><input name='model' type='text' style='width:100%' value='gpt-4o'></label><br><br>
<button type='submit'>Save</button>
</form>
<p>After saving, open <a href='http://localhost:3000'>Chat (Open WebUI on :3000)</a> — it is pre-wired to <code>http://screenipy:8000/v1</code>.</p>
</body></html>"""
        return HTMLResponse(html)

    @app.post("/setup")
    async def setup_post(request: __import__('fastapi').Request):
        # Accept both JSON and form
        ctype = (request.headers.get("content-type") or "").lower()
        data = {}
        if "application/json" in ctype:
            try:
                data = await request.json()
            except Exception:
                raise HTTPException(status_code=400, detail="invalid JSON")
        else:
            try:
                form = await request.form()
                data = {k: v for k, v in form.items()}
            except Exception:
                # Fallback without python-multipart: parse urlencoded body
                from urllib.parse import parse_qs
                body = await request.body()
                qs = parse_qs(body.decode() if isinstance(body, (bytes, bytearray)) else str(body))
                data = {k: v[0] if isinstance(v, list) else v for k, v in qs.items()}
        try:
            p = save_byok(data)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        # Never echo raw key
        return {"status": "ok", "path": str(p), "byok": redacted(load_byok(p))}

    @app.get("/byok")
    def byok_status():
        data = load_byok()
        return {"configured": data is not None, "path": str(byok_path()), "byok": redacted(data)}

    @app.get("/v1/models")
    def list_models():
        now = int(time.time())
        return {
            "object": "list",
            "data": [
                {"id": m["id"], "object": "model", "created": now, "owned_by": m.get("owned_by", "screenipy")}
                for m in MODEL_PRESETS
            ],
        }

    @app.get("/v1/skills")
    def list_skills():
        return {
            "skills": sorted(_eng.skills.keys()),
            "default_strategy_pack": DEFAULT_STRATEGY_PACK,
            "rejections": _eng.chat_visible_rejections(),
        }

    @app.get("/v1/presets")
    def list_presets():
        return {
            "models": MODEL_PRESETS,
            "default_strategy_pack": DEFAULT_STRATEGY_PACK,
            "skills": sorted(_eng.skills.keys()),
        }

    @app.post("/v1/chat/completions")
    def chat_completions(req: ChatCompletionRequest):
        if not req.messages:
            raise HTTPException(status_code=400, detail="messages: required non-empty list")
        if req.stream:
            raise HTTPException(status_code=400, detail="stream: not supported in 301")
        # Normalize messages to dicts
        msgs = [{"role": m.role, "content": m.content} for m in req.messages]
        query = _last_user_message(msgs)
        if not query or not query.strip():
            raise HTTPException(status_code=400, detail="last user message must be non-empty")

        # Freshness HITL detection: if query is literally fresh/stale, preserve prior query context
        user_choice = _detect_freshness_choice(msgs)
        # If the user just said 'fresh'/'stale', the real intent is the previous user query
        # before the stale-block. Find that prior query for skill routing.
        effective_query = query
        if user_choice and len(msgs) >= 3:
            # msgs[-1] is fresh/stale, msgs[-2] is assistant stale block, msgs[-3] is original user intent
            for m in reversed(msgs[:-1]):
                if m["role"] == "user":
                    effective_query = m["content"]
                    break

        explicit = _extract_explicit_skill_from_messages(msgs)
        index = _extract_index_from_messages(msgs)

        # Rejection visibility: if the user asked for an invalid skill file name that was rejected, surface it
        if explicit and explicit not in _eng.skills:
            # check if rejection mentions that explicit name? We surface generic rejection list
            rejs = _eng.chat_visible_rejections()
            if rejs:
                content = f"Skill '{explicit}' is not available. " + " ".join(rejs[:2])
                return _build_chat_response(req.model, content)

        # If there are rejections from custom skills, they are chat-visible via payload? Spec says
        # invalid files rejected with chat-visible error naming the problem. We don't spam every reply,
        # but we expose them on /v1/skills and also when the user asks about skills.

        content = _eng.answer(effective_query, user_choice=user_choice, explicit_skill=explicit, index=index)

        # If the engine emitted rejections and the user is asking about skills/custom, append them
        if "skill" in query.lower() and _eng.rejections:
            content += "\n\n" + "\n".join(_eng.chat_visible_rejections()[:3])

        return _build_chat_response(req.model, content)

    return app

# Convenience for uvicorn CLI
app = None
try:
    if _FASTAPI_AVAILABLE:
        app = create_app()
except Exception:
    app = None

def run(host: str = "127.0.0.1", port: int = 8000):
    import uvicorn
    uvicorn.run(create_app(), host=host, port=port)
