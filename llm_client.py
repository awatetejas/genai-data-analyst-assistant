"""OpenRouter client for question classification and result explanations."""
import json
import os
import re

import requests
from dotenv import load_dotenv

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
ALLOWED_ANALYSES = [
    "total_revenue", "total_profit", "average_order_value",
    "revenue_by_category", "top_products", "revenue_by_region",
    "monthly_revenue", "dataset_summary", "unsupported",
]


class LLMError(RuntimeError):
    """Raised when the LLM request fails or returns unusable output."""


def _chat_completion(messages, temperature=0.1):
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "your_openrouter_api_key_here":
        raise LLMError("OPENROUTER_API_KEY is missing. Add your key to the local .env file.")
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "GenAI-Powered Data Analyst Assistant",
    }
    try:
        response = requests.post(
            OPENROUTER_URL, headers=headers,
            json={"model": OPENROUTER_MODEL, "messages": messages, "temperature": temperature},
            timeout=60,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise LLMError("The model returned an empty response.")
        return content.strip()
    except requests.RequestException as exc:
        raise LLMError(f"OpenRouter request failed: {exc}") from exc
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise LLMError("OpenRouter returned an unexpected response.") from exc


def _recent_messages(conversation_history):
    messages = []
    for item in (conversation_history or [])[-6:]:
        role, content = item.get("role"), item.get("content")
        if role in {"user", "assistant"} and isinstance(content, str):
            messages.append({"role": role, "content": content[:1500]})
    return messages


def classify_question(question, columns, conversation_history=None):
    system_prompt = f"""
You route questions for a data analytics application.
Choose exactly one value from this allowlist: {json.dumps(ALLOWED_ANALYSES)}
Return ONLY JSON in this exact shape: {{"analysis": "allowlisted_value"}}
Available dataset columns: {json.dumps(list(columns))}.
Use recent conversation context to interpret follow-ups. Choose "unsupported"
for unrelated questions or requests that do not fit a listed analysis.
Choose "dataset_summary" for a general overview. Never generate code, SQL,
formulas, extra keys, or explanations.
"""
    messages = [{"role": "system", "content": system_prompt.strip()}]
    messages.extend(_recent_messages(conversation_history))
    messages.append({"role": "user", "content": question})
    raw = _chat_completion(messages, temperature=0)
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise LLMError("The model did not return valid JSON. Please rephrase.") from exc
    if not isinstance(result, dict) or result.get("analysis") not in ALLOWED_ANALYSES:
        raise LLMError("The model selected an unsupported analysis.")
    return result["analysis"]


def explain_result(question, analysis_name, result, conversation_history=None):
    system_prompt = """
You are a careful data analyst assistant. Explain only the Python-computed
result supplied to you. Do not invent numbers, columns, causes, trends, or
business context. Distinguish observed patterns from possible explanations.
If the result is insufficient, say so. Use concise language and format sales
amounts in Indian rupees. Do not claim causation from correlation.
"""
    messages = [{"role": "system", "content": system_prompt.strip()}]
    messages.extend(_recent_messages(conversation_history))
    messages.append({
        "role": "user",
        "content": json.dumps({
            "question": question,
            "analysis": analysis_name,
            "python_computed_result": result,
        }, default=str),
    })
    return _chat_completion(messages, temperature=0.2)
