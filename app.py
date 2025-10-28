# backend/app.py
import os
import json
import re
from typing import List, Dict, Any, Optional
from flask import Flask, request, jsonify
from flask_cors import CORS
from pydantic import BaseModel, ValidationError, conint
from dotenv import load_dotenv

load_dotenv()

# Optional OpenAI integration:
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
CORS(app, origins="*")  # tighten origins in production

# If openai is available and key present, we'll use it.
USE_OPENAI = False
if OPENAI_API_KEY:
    try:
        import openai
        openai.api_key = OPENAI_API_KEY
        USE_OPENAI = True
    except Exception:
        USE_OPENAI = False

# --- Input validation model ---
class GenerateRequest(BaseModel):
    text: str
    type: str  # "MCQ", "FIB", "T/F"
    count: conint(ge=1, le=15) = 5  # between 1 and 15

# --- Helpers ---
def word_count(s: str) -> int:
    return len([w for w in re.split(r"\s+", s) if w.strip()])

def validate_request(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        req = GenerateRequest(**payload)
    except ValidationError as e:
        return {"error": e.errors()}
    # ensure minimum 100 words
    if word_count(req.text) < 100:
        return {"error": "Input must contain at least 100 words."}
    if req.type not in ("MCQ", "FIB", "T/F"):
        return {"error": "Invalid type. Choose one of: MCQ, FIB, T/F."}
    return {"ok": True, "req": req}

# --- Prompt templates ---
def build_prompt(text: str, qtype: str, count: int) -> str:
    """
    Build a carefully engineered prompt for the LLM to produce a strict JSON output.
    The model is instructed to respond with an array of objects. Each object:
      {
        "question": "...",
        "options": ["a", "b", "c", "d"],            # only for MCQ
        "answer": "a" | "True" | "False" | "short text",
        "explanation": "..."
      }
    """
    instruction = (
        "You are an expert educational content author. Carefully read the source text provided below and "
        "generate exactly {count} {qtype} questions that are accurate, unambiguous, and test the main ideas, "
        "important facts, and conceptual understanding. Use appropriate difficulty for high-school/college-level learners "
        "unless the user specifies otherwise. Keep each question self-contained.\n\n"
        "REPLY STRICTLY IN JSON: produce a JSON array (no surrounding commentary) where each element has these keys:\n"
        " - question: string\n"
        " - options: array of strings (ONLY for MCQ; for other types use an empty array)\n"
        " - answer: string (for MCQ give the correct option text; for T/F use 'True' or 'False'; for FIB give the single-word/phrase expected)\n"
        " - explanation: string (brief explanation of the correct answer; 1-2 sentences)\n\n"
        "If MCQ: produce 3-5 plausible choices. Distractors should be plausible but clearly incorrect upon reasoning.\n"
        "If FIB: create a short sentence with a single blank, and the 'answer' should be the missing word/phrase.\n"
        "If T/F: produce clear factual statements that are either True or False.\n\n"
        "Output example (for MCQ):\n"
        "[{{\"question\":\"...\",\"options\":[\"A\",\"B\",\"C\",\"D\"],\"answer\":\"B\",\"explanation\":\"...\"}}, ...]\n\n"
    ).format(count=count, qtype=qtype)

    # Keep the text compacted — the model sees the full text
    payload = f"{instruction}\nSOURCE TEXT:\n{'''\n'''.join(text.strip().splitlines())}\n\n"
    return payload

# --- Model call ---
def call_llm(prompt: str, max_tokens: int = 800, temperature: float = 0.2) -> str:
    """
    Call LLM via OpenAI if available. Otherwise return empty string (caller should fallback).
    """
    if USE_OPENAI:
        # Use a chat completion if available, otherwise fallback to completion endpoint.
        try:
            # use gpt-4.1-mini or gpt-4o if available, otherwise fallback to gpt-3.5-turbo
            model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
            resp = openai.ChatCompletion.create(
                model=model,
                messages=[{"role":"system","content":"You are a helpful content generation assistant."},
                          {"role":"user","content":prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                n=1
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            app.logger.exception("OpenAI call failed")
            raise
    else:
        # No API — let caller handle fallback.
        return ""

# --- Simple deterministic offline fallback generator ---
def fallback_generate(text: str, qtype: str, count: int) -> List[Dict[str, Any]]:
    """
    Very simple deterministic question generator for testing without an LLM.
    It extracts key sentences and creates surface-level questions.
    Not a substitute for an LLM, but useful to test pipelines.
    """
    # gather candidate sentences
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    # pick sentences spread across the text
    chosen = []
    if not sentences:
        sentences = [text]
    step = max(1, len(sentences)//max(1,count))
    idx = 0
    for i in range(count):
        chosen.append(sentences[min(idx, len(sentences)-1)])
        idx += step

    results = []
    for i, sent in enumerate(chosen):
        if qtype == "MCQ":
            # create a simple question: "Which of the following is true about X?"
            key = re.sub(r'<[^>]+>', '', sent).strip()
            q = f"According to the text, which of the following is true about: \"{key[:60]}...\"?"
            correct = key[:40].rstrip('.')
            # make 3 distractors by simple permutations
            options = [
                correct,
                correct + " (incorrect variant A)",
                "A commonly mistaken statement",
                "An unrelated plausible-sounding statement"
            ][:4]
            results.append({"question": q, "options": options, "answer": options[0], "explanation": f"Based on the passage: {key[:120]}."})
        elif qtype == "FIB":
            # pick a word to blank
            words = [w for w in re.findall(r"\w+", sent) if len(w) > 3]
            blank = words[0] if words else sent.strip()
            q = sent.replace(blank, "_____")
            results.append({"question": q, "options": [], "answer": blank, "explanation": f"The missing word is '{blank}' as in the text."})
        else:  # T/F
            # make statement from sentence and mark True
            q = sent.strip()
            results.append({"question": q, "options": [], "answer": "True", "explanation": "This statement is directly from the source text."})
    return results

# --- parse model output robustly ---
def parse_llm_json(resp_text: str) -> List[Dict[str, Any]]:
    """
    Attempt to extract JSON array from model output.
    The LLM is instructed to return strict JSON array; this routine finds the first '[' ... ']' and loads it.
    """
    # find first JSON array
    m = re.search(r'(\[.*\])', resp_text, flags=re.S)
    if not m:
        raise ValueError("No JSON array found in LLM response.")
    json_text = m.group(1)
    # fix common trailing commas or single-quotes
    json_text = re.sub(r",\s*}", "}", json_text)
    json_text = re.sub(r",\s*\]", "]", json_text)
    # replace smart quotes
    json_text = json_text.replace("“", '"').replace("”", '"').replace("’", "'")
    # try loading
    data = json.loads(json_text)
    if not isinstance(data, list):
        raise ValueError("Parsed JSON is not a list.")
    return data

# --- Route ---
@app.route("/api/generate", methods=["POST"])
def generate():
    payload = request.get_json(force=True)
    v = validate_request(payload)
    if v.get("error"):
        return jsonify({"ok": False, "error": v["error"]}), 400
    req = v["req"]

    prompt = build_prompt(req.text, req.type, req.count)
    # If we have an LLM, call it
    if USE_OPENAI:
        try:
            model_out = call_llm(prompt, max_tokens=900, temperature=0.2)
            parsed = parse_llm_json(model_out)
            # Basic validation and trimming:
            for q in parsed:
                q.setdefault("options", [])
                q.setdefault("explanation", "")
                q.setdefault("answer", "")
                q["question"] = str(q["question"]).strip()
            return jsonify({"ok": True, "source": "openai", "questions": parsed})
        except Exception as e:
            app.logger.exception("LLM parsing failed; falling back.")
            # fall back to deterministic generator
            fallback = fallback_generate(req.text, req.type, req.count)
            return jsonify({"ok": True, "source": "fallback", "questions": fallback})
    else:
        # No API key — fallback deterministic generator
        fallback = fallback_generate(req.text, req.type, req.count)
        return jsonify({"ok": True, "source": "fallback", "questions": fallback})


if __name__ == "__main__":
    # run dev server
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
