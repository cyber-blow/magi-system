import os
import asyncio
import re
import json
import datetime
import random
import requests
import uuid
from typing import List, Tuple, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# PDF Analysis
import PyPDF2
import io

# AI Providers
import google.generativeai as genai
from groq import AsyncGroq
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

# --- 1. Constants & Paths ---

BASE_DIR = os.path.dirname(__file__)
PERSONA_PATH = os.path.join(BASE_DIR, "personas.json")
API_KEYS_PATH = os.path.join(BASE_DIR, "api_keys.json")
HISTORY_PATH = os.path.join(BASE_DIR, "history.json")
TEMPLATES_PATH = os.path.join(BASE_DIR, "templates.json")
USERS_PATH = os.path.join(BASE_DIR, "users.json")
WEBHOOKS_PATH = os.path.join(BASE_DIR, "webhooks.json")
SESSIONS_PATH = os.path.join(BASE_DIR, "sessions.json")

# Output format instruction for consistent parsing
OUTPUT_INSTRUCTION = """
【重要：出力形式の遵守】
1. 回答は**プレーンテキストのみ**で行ってください。HTMLタグ（<div>など）やMarkdownのコードブロックは絶対に使用しないでください。
2. 回答の最後には、結論として以下のいずれか1つを必ず【】で囲んで出力してください。

選択肢:
1. 【是認】
2. 【条件付是認】
3. 【否認】

出力フォーマット:
理由: (思考プロセス)
条件: (条件付是認の場合のみ記述。なければ「なし」)
結論: 【是認】
"""

# SEELE Synthesis Prompt
SEELE_PROMPT = """
あなたはゼーレ（SEELE）の最高幹部であり、MAGIシステムの審議結果を総括する責任者です。
メルキオール、バルタザール、カスパーの3つの意見を統合し、組織としての最終的な意思決定および戦略的助言を行ってください。

【入力データ】
- 審議事項: {question}
- メルキオールの意見: {m_opinion}
- バルタザールの意見: {b_opinion}
- カスパーの意見: {c_opinion}

【出力内容】
1. 結論の要約（是認・条件付・否認の背景）
2. 懸念点とその対策
3. 戦略的アドバイス
"""

# --- 2. Configuration & Data Management (JSON) ---

def load_json(path: str, default: Any) -> Any:
    """Load JSON file safely, returning default if missing or invalid."""
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {path}: {e}")
    return default

def save_json(path: str, data: Any) -> None:
    """Save data to JSON file with UTF-8 encoding."""
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving {path}: {e}")

def load_persona_config() -> Dict[str, Any]:
    """Load persona configurations (Melchior, Balthasar, Casper)."""
    return load_json(PERSONA_PATH, {})

def save_persona_config(config: Dict[str, Any]) -> None:
    """Save persona configurations."""
    save_json(PERSONA_PATH, config)

def load_api_config() -> Dict[str, Any]:
    """Load API provider settings and available models."""
    default_config = {
        "seele_model": {"provider": "google", "name": "gemini-2.0-flash"},
        "providers": {
            "google": {"api_key": "", "models": []},
            "groq": {"api_key": "", "models": []},
            "openai": {"api_key": "", "models": []},
            "anthropic": {"api_key": "", "models": []},
            "local": {"api_key": "not-needed", "base_url": "http://localhost:11434/v1", "models": []}
        }
    }
    data = load_json(API_KEYS_PATH, default_config)
    # Ensure structure integrity
    if "providers" not in data: data["providers"] = default_config["providers"]
    if "seele_model" not in data: data["seele_model"] = default_config["seele_model"]
    if "local" not in data["providers"]: data["providers"]["local"] = default_config["providers"]["local"]
    return data

def save_api_config(config: Dict[str, Any]) -> None:
    """Save API provider settings."""
    save_json(API_KEYS_PATH, config)

def add_history(question: str, results: List[Tuple[str, str, str, str]], final_score: int, seele_summary: str = "", file_name: str = "") -> None:
    """Legacy wrapper for adding history (without user context)."""
    history = load_json(HISTORY_PATH, [])
    entry = {
        "id": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
        "timestamp": datetime.datetime.now().isoformat(),
        "question": question,
        "file_name": file_name,
        "results": [{"name": r[0], "reason": r[1], "vote": r[2], "condition": r[3]} for r in results],
        "final_score": final_score,
        "seele_summary": seele_summary
    }
    history.insert(0, entry)
    save_json(HISTORY_PATH, history[:100])

def add_history_with_user(user_id: str, question: str, results: List[Tuple[str, str, str, str]], final_score: int, seele_summary: str = "", file_name: str = "") -> None:
    """Record a deliberation session into history.json with user context."""
    history = load_json(HISTORY_PATH, [])
    entry = {
        "id": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
        "timestamp": datetime.datetime.now().isoformat(),
        "user_id": user_id,
        "question": question,
        "file_name": file_name,
        "results": [{"name": r[0], "reason": r[1], "vote": r[2], "condition": r[3]} for r in results],
        "final_score": final_score,
        "seele_summary": seele_summary
    }
    history.insert(0, entry)
    save_json(HISTORY_PATH, history[:100]) # Keep last 100 entries

def execute_webhook_action(webhook_id: str, title: str, text: str) -> bool:
    """Execute an external webhook action (Slack/Discord)."""
    webhooks = load_json(WEBHOOKS_PATH, {"webhooks": {}}).get("webhooks", {})
    cfg = webhooks.get(webhook_id)
    if not cfg or not cfg.get("url"): return False
    
    try:
        payload = {"text": f"【MAGI SYSTEM DECISION】\n*Topic*: {title}\n\n{text}"}
        res = requests.post(cfg["url"], json=payload, timeout=10)
        return res.status_code < 300
    except Exception as e:
        print(f"Webhook failed: {e}")
        return False

# --- 3. User Authentication & Session Management ---

def authenticate_user(username: str, password: str) -> Optional[Dict[str, str]]:
    """Verify user credentials against users.json."""
    users_data = load_json(USERS_PATH, {"users": {}})
    user = users_data.get("users", {}).get(username)
    if user and user["password"] == password:
        return {"username": username, "name": user["name"], "role": user["role"]}
    return None

def add_user(username: str, password: str, name: str, role: str) -> bool:
    """Register a new user."""
    users_data = load_json(USERS_PATH, {"users": {}})
    if username in users_data["users"]: return False
    users_data["users"][username] = {"password": password, "name": name, "role": role}
    save_json(USERS_PATH, users_data)
    return True

def delete_user(username: str) -> bool:
    """Delete a user, preventing deletion of root admin."""
    users_data = load_json(USERS_PATH, {"users": {}})
    if username == "nerv_admin": return False # Prevent deleting root
    if username in users_data["users"]:
        del users_data["users"][username]
        save_json(USERS_PATH, users_data)
        return True
    return False

def get_all_users() -> Dict[str, Dict[str, str]]:
    """Retrieve all properly registered users."""
    return load_json(USERS_PATH, {"users": {}}).get("users", {})

def create_session(user_info: Dict[str, str]) -> str:
    """Create a new persistent session and return the token."""
    token = str(uuid.uuid4())
    sessions = load_json(SESSIONS_PATH, {})
    sessions[token] = {
        "user": user_info,
        "created_at": datetime.datetime.now().isoformat()
    }
    save_json(SESSIONS_PATH, sessions)
    return token

def validate_session(token: str) -> Optional[Dict[str, str]]:
    """Validate a session token and return user info if valid."""
    sessions = load_json(SESSIONS_PATH, {})
    sess = sessions.get(token)
    if sess:
        # Optional: Add expiration check here logic in future
        return sess["user"]
    return None

def clear_session(token: str) -> None:
    """Invalidate a specific session token."""
    sessions = load_json(SESSIONS_PATH, {})
    if token in sessions:
        del sessions[token]
        save_json(SESSIONS_PATH, sessions)

# --- 4. Client Management ---

def get_clients() -> Dict[str, Any]:
    """Initialize and return AI clients based on configuration."""
    api_config = load_api_config()
    providers = api_config.get("providers", {})
    clients = {"google": None, "groq": None, "openai": None, "anthropic": None, "local": None}
    
    if providers.get("google", {}).get("api_key"):
        try: genai.configure(api_key=providers["google"]["api_key"]); clients["google"] = True
        except Exception: pass
    if providers.get("groq", {}).get("api_key"):
        try: clients["groq"] = AsyncGroq(api_key=providers["groq"]["api_key"])
        except Exception: pass
    if providers.get("openai", {}).get("api_key"):
        try: clients["openai"] = AsyncOpenAI(api_key=providers["openai"]["api_key"])
        except Exception: pass
    if providers.get("anthropic", {}).get("api_key"):
        try: clients["anthropic"] = AsyncAnthropic(api_key=providers["anthropic"]["api_key"])
        except Exception: pass
    if providers.get("local", {}).get("base_url"):
        try: clients["local"] = AsyncOpenAI(api_key=providers["local"].get("api_key", "sk-xxx"), base_url=providers["local"]["base_url"])
        except Exception as e: print(f"Local client failed: {e}")
    return clients

# --- 5. Model Fetching Utilities ---

async def fetch_models_google(api_key: str) -> List[str]:
    try:
        genai.configure(api_key=api_key)
        await asyncio.sleep(0.5)
        return sorted(list(set([m.name.replace("models/", "") for m in genai.list_models() if 'generateContent' in m.supported_generation_methods])))
    except Exception: return ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"]

async def fetch_models_groq(api_key: str) -> List[str]:
    try:
        client = AsyncGroq(api_key=api_key)
        models = await client.models.list()
        return [m.id for m in models.data]
    except Exception: return ["llama3-8b-8192", "mixtral-8x7b-32768"]

async def fetch_models_openai(api_key: str) -> List[str]:
    try:
        client = AsyncOpenAI(api_key=api_key)
        models = await client.models.list()
        return [m.id for m in models.data if "gpt" in m.id]
    except Exception: return ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]

async def fetch_models_anthropic(api_key: str) -> List[str]:
    return ["claude-3-5-sonnet-20240620", "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"]

async def fetch_models_local(base_url: str, api_key: str = "sk-xxx") -> List[str]:
    try:
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        models = await client.models.list()
        return [m.id for m in models.data]
    except Exception as e:
        print(f"Local model fetch failed: {e}")
        return ["local-model-error"]

# --- 6. File Analysis ---

def extract_text_from_file(file_content: bytes, file_name: str) -> str:
    """Extract text from PDF or TXT files."""
    if file_name.endswith('.pdf'):
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        except Exception: return "[Error extracting PDF text]"
    elif file_name.endswith('.txt'):
        return file_content.decode('utf-8', errors='ignore')
    return ""

# --- 7. Core AI Logic (Retry & Execution) ---

class RateLimitError(Exception): pass

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((RateLimitError, Exception)),
    reraise=True
)
async def call_provider_with_retry(provider: str, model: str, sys_prompt: str, user_prompt: str, temp: float, clients: Dict, max_tokens: int = 4096, top_p: float = 1.0) -> str:
    """Call an AI provider with robust error handling and retry logic."""
    try:
        client = clients.get(provider)
        if not client: raise Exception(f"Provider {provider} not configured.")

        if provider == "google":
            m = genai.GenerativeModel(model)
            response = await asyncio.to_thread(m.generate_content, sys_prompt + "\n\n" + user_prompt, 
                                             generation_config=genai.types.GenerationConfig(temperature=temp, top_p=top_p, max_output_tokens=max_tokens))
            return response.text
        elif provider in ["groq", "openai", "local"]:
            completion = await client.chat.completions.create(model=model, messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_prompt}], temperature=temp, top_p=top_p, max_tokens=max_tokens)
            return completion.choices[0].message.content
        elif provider == "anthropic":
            message = await client.messages.create(model=model, max_tokens=max_tokens, system=sys_prompt, messages=[{"role": "user", "content": user_prompt}], temperature=temp, top_p=top_p)
            return message.content[0].text
        else: raise ValueError(f"Unknown provider: {provider}")
    except Exception as e:
        if "429" in str(e) or "quota" in str(e).lower():
            raise RateLimitError(str(e))
        raise e

def parse_response(name: str, text: str) -> Tuple[str, str, str, str]:
    """Parse the raw AI response into structured data."""
    clean_text = re.sub(r'<[^>]+>', '', text)
    clean_text = clean_text.replace("```html", "").replace("```", "").strip()
    vote = "否認"; condition = "特になし"
    if "条件付是認" in clean_text or "【条件付是認】" in clean_text: vote = "条件付是認"
    elif "是認" in clean_text or "【是認】" in clean_text: vote = "是認"
    
    cond_match = re.search(r"(?:条件|Condition)[:：]\s*(.+)", clean_text, re.MULTILINE)
    if cond_match:
        condition = cond_match.group(1).strip()
        if condition.lower() in ["なし", "none", "無し", "特になし", ""]: condition = ""
    return name, clean_text, vote, condition

async def ask_philosopher(philosopher_id: str, question: str, context: str = "", other_opinions: str = "", debate: bool = False, delay: float = 0) -> Tuple[str, str, str, str]:
    """Execute a deliberation sequence for a single MAGI unit."""
    if delay > 0: await asyncio.sleep(delay)
    
    config = load_persona_config().get(philosopher_id)
    if not config: return (philosopher_id, "Config Missing", "否認", "設定不足")

    sys_prompt = config['prompt'] + OUTPUT_INSTRUCTION
    prompt_with_context = f"【参考資料】\n{context}\n\n審議事項: {question}\n{OUTPUT_INSTRUCTION}" if context else f"審議事項: {question}\n{OUTPUT_INSTRUCTION}"
    
    user_prompt = prompt_with_context
    if debate and other_opinions:
        user_prompt = f"以下の他者の意見を読み込み、議論を深めた上であなたの最終結論を出してください。\n\n【他者の第一回意見】\n{other_opinions}\n\n{prompt_with_context}"
    
    clients = get_clients()
    try:
        raw_res = await call_provider_with_retry(
            config["model_provider"], config["model_name"], sys_prompt, user_prompt, 
            config.get("temperature", 0.7), clients, int(config.get("max_tokens", 4096)), config.get("top_p", 1.0)
        )
        return parse_response(config["name"], raw_res)
    except Exception as e:
        return (config["name"], f"AI Error: {str(e)}", "否認", "エラー発生")

async def ask_magi_system(question: str, context: str = "", debate: bool = False, synthesis: bool = True, file_name: str = "") -> Dict[str, Any]:
    """Orchestrate the entire MAGI deliberation process (3 Magi + Seele)."""
    tasks = [
        ask_philosopher("MELCHIOR", question, context, delay=0),
        ask_philosopher("BALTHASAR", question, context, delay=0.5),
        ask_philosopher("CASPER", question, context, delay=1.0)
    ]
    results = list(await asyncio.gather(*tasks))
    
    if debate:
        opinions_str = "\n---\n".join([f"{r[0]}: {r[1]}" for r in results])
        tasks_round2 = [
            ask_philosopher("MELCHIOR", question, context, opinions_str, debate=True, delay=0),
            ask_philosopher("BALTHASAR", question, context, opinions_str, debate=True, delay=0.5),
            ask_philosopher("CASPER", question, context, opinions_str, debate=True, delay=1.0)
        ]
        results = list(await asyncio.gather(*tasks_round2))

    score_map = {"是認": 1, "条件付是認": 0, "否認": -1}
    final_score = sum([score_map.get(r[2], -1) for r in results])
    
    summary = ""
    if synthesis:
        try:
            api_config = load_api_config()
            seele_cfg = api_config.get("seele_model", {"provider": "google", "name": "gemini-2.0-flash"})
            o_str = { "m": results[0][1], "b": results[1][1], "c": results[2][1] }
            user_p = SEELE_PROMPT.format(question=question, m_opinion=o_str["m"], b_opinion=o_str["b"], c_opinion=o_str["c"])
            clients = get_clients()
            summary = await call_provider_with_retry(seele_cfg["provider"], seele_cfg["name"], "SEELE SYSTEM ACTIVE.", user_p, 0.4, clients)
        except Exception as e:
            summary = f"【警告】ゼーレの介入に失敗しました（{str(e)}）。三賢者の個別判断を確認してください。"
    
    # Legacy support, though add_history_with_user is preferred in implementation
    # This prevents errors if called directly.
    # add_history(question, results, final_score, summary, file_name)
    
    return {"magi_results": results, "final_score": final_score, "seele_summary": summary}