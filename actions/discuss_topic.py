# actions/discuss_topic.py
"""
Multi‑agent discussion module for P.E.K.A.

When the user asks to "discuss" a topic, this module:
1. Runs several Gemini instances in parallel (using different API keys / personas).
2. Collects diverse perspectives.
3. Synthesises the best answer through a moderator.
4. Returns a final, deeply considered response.

Personas:
- Logical Analyst: focuses on reasoning, structure, pros/cons.
- Creative Thinker: explores novel ideas, metaphors, possibilities.
- Critical Reviewer: finds flaws, assumptions, missing points.
- Practical Executor: focuses on real‑world applicability, steps.
- Scientific Mind: demands evidence, data, precise definitions.

Each persona uses a separate API key (if available) to avoid rate limiting.
"""

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Any, Optional

from google import genai

# ─── Path to API keys config (same as used in main.py) ─────────
def _get_base_dir() -> Path:
    import sys
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = _get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"

# ─── Global key cycler (thread‑safe) ──────────────────────────
_key_lock = threading.Lock()
_key_cycle_index = 0
_cached_keys: List[str] = []

def _load_keys() -> List[str]:
    global _cached_keys
    if not _cached_keys:
        with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Supports both old single key and new array format
        if "gemini_api_keys" in data:
            keys = data["gemini_api_keys"]
        elif "gemini_api_key" in data:
            keys = [data["gemini_api_key"]]
        else:
            raise ValueError("No Gemini API keys found in config.")
        _cached_keys = keys
    return _cached_keys

def _get_next_key() -> str:
    """Thread‑safe round‑robin key selection."""
    global _key_cycle_index
    keys = _load_keys()
    with _key_lock:
        key = keys[_key_cycle_index % len(keys)]
        _key_cycle_index += 1
        return key

def _call_gemini(prompt: str, model: str = "gemini-2.5-flash", max_retries: int = 2) -> str:
    """Call Gemini with automatic key rotation on failure."""
    for attempt in range(max_retries + 1):
        try:
            key = _get_next_key()
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model=model,
                contents=prompt,
            )
            return response.text.strip()
        except Exception:
            if attempt == max_retries:
                raise
            time.sleep(0.5 * (attempt + 1))
    return "Error: unable to get response."

# ─── Persona definitions ──────────────────────────────────────
PERSONAS = {
    "logical": {
        "role": "Logical Analyst",
        "instruction": (
            "You are a Logical Analyst. Your task is to break down the topic, "
            "identify core arguments, weigh pros and cons, and structure the reasoning "
            "clearly. Be objective and systematic. Avoid emotional language."
        )
    },
    "creative": {
        "role": "Creative Thinker",
        "instruction": (
            "You are a Creative Thinker. Your task is to explore unconventional ideas, "
            "analogies, metaphors, and lateral connections. Think outside the box. "
            "Generate novel possibilities and imaginative interpretations."
        )
    },
    "critical": {
        "role": "Critical Reviewer",
        "instruction": (
            "You are a Critical Reviewer. Your task is to find weaknesses, assumptions, "
            "logical fallacies, omitted counterarguments, and potential blind spots. "
            "Be rigorous and skeptical. Point out what others might miss."
        )
    },
    "practical": {
        "role": "Practical Executor",
        "instruction": (
            "You are a Practical Executor. Your task is to focus on real‑world applicability, "
            "step‑by‑step actions, feasibility, resources, and implementation details. "
            "Give actionable advice and concrete examples."
        )
    },
    "scientific": {
        "role": "Scientific Mind",
        "instruction": (
            "You are a Scientific Mind. Your task is to demand evidence, data, precise "
            "definitions, causality, and reproducibility. Be methodical and cite "
            "principles where possible. Avoid speculation without proof."
        )
    }
}

# Default personas to use (can be overridden by user)
DEFAULT_PERSONAS = ["logical", "creative", "critical", "practical", "scientific"]

def _run_single_persona(persona_name: str, topic: str, extra_context: str = "") -> Dict[str, Any]:
    """Call Gemini with a specific persona and return the response."""
    persona = PERSONAS.get(persona_name)
    if not persona:
        return {"persona": persona_name, "error": f"Unknown persona: {persona_name}"}
    
    prompt = f"""{persona['instruction']}

Topic to discuss: {topic}

{extra_context}

Now provide your analysis and perspective on the topic. Be thorough but concise (around 200‑300 words)."""
    
    try:
        response = _call_gemini(prompt)
        return {"persona": persona_name, "role": persona['role'], "response": response}
    except Exception as e:
        return {"persona": persona_name, "role": persona['role'], "error": str(e)}

def _synthesize(contributions: List[Dict[str, Any]], topic: str, user_question: str = "") -> str:
    """
    Moderator: take all contributions and produce the best final answer.
    """
    contributions_text = ""
    for c in contributions:
        if "error" in c:
            contributions_text += f"[{c['role'] if 'role' in c else c['persona']}] Error: {c['error']}\n\n"
        else:
            contributions_text += f"[{c['role']}]\n{c['response']}\n\n"
    
    moderator_prompt = f"""
You are a wise Moderator and Synthesizer. Your task is to read all the different perspectives below on the topic:
"{topic}"

User's specific question (if any): {user_question if user_question else "No specific question, just discuss the topic."}

Then produce a single, final answer that:
1. Integrates the strongest insights from each perspective.
2. Resolves contradictions by prioritising the most logical and evidence‑based views.
3. Presents the conclusion in a clear, helpful, and engaging way.
4. Is suitable for speaking aloud (natural, conversational tone).

Do not simply summarise each contribution. Synthesise them into a cohesive, improved answer.

Here are the contributions:
{contributions_text}

Final synthesised answer (speak directly to the user):
"""
    return _call_gemini(moderator_prompt)

def _second_round_refinement(initial_synthesis: str, contributions: List[Dict[str, Any]], topic: str) -> str:
    """
    Optional second round: ask each persona to critique/improve the synthesis,
    then synthesise again.
    """
    # First, collect critiques
    critique_prompts = []
    for c in contributions:
        if "error" in c:
            continue
        persona_name = c['persona']
        persona = PERSONAS[persona_name]
        prompt = f"""{persona['instruction']}

You previously gave your thoughts on the topic: "{topic}"

Now here is a synthesised answer that tries to combine all perspectives:
{initial_synthesis}

As a {persona['role']}, please critique this synthesis. What did it miss or get wrong from your perspective? Suggest specific improvements. Keep it concise (max 150 words)."""
        critique_prompts.append((persona_name, persona['role'], prompt))
    
    # Run critiques in parallel
    critiques = []
    with ThreadPoolExecutor(max_workers=len(critique_prompts)) as executor:
        future_to_persona = {}
        for pname, role, p in critique_prompts:
            future_to_persona[executor.submit(_call_gemini, p)] = (pname, role)
        for future in as_completed(future_to_persona):
            pname, role = future_to_persona[future]
            try:
                crit = future.result()
                critiques.append(f"[{role} critique]\n{crit}")
            except Exception as e:
                critiques.append(f"[{role} critique] Error: {e}")
    
    critiques_text = "\n\n".join(critiques)
    
    final_prompt = f"""
You are the Moderator again. After receiving critiques of your synthesis, produce the final, polished answer.

Topic: "{topic}"

Original synthesis:
{initial_synthesis}

Critiques and suggestions:
{critiques_text}

Now produce the **final answer** that addresses the critiques and is even stronger. Speak naturally, as if to the user.
"""
    return _call_gemini(final_prompt)

# ─── Main entry point to be called from main.py ───────────────
def discuss_topic(
    topic: str,
    user_question: str = "",
    personas: Optional[List[str]] = None,
    two_rounds: bool = True,
    player = None,
    speak = None
) -> str:
    """
    Args:
        topic: The main subject to discuss.
        user_question: Optional specific question about the topic.
        personas: List of persona keys to use (default: all five).
        two_rounds: Whether to do a second round of critique/refinement.
        player: UI log object (must have write_log method).
        speak: Function to speak the final answer.

    Returns:
        Final synthesised answer as a string.
    """
    if player:
        player.write_log(f"[DISCUSS] Starting multi‑agent discussion on: {topic}")
    
    if personas is None:
        personas = DEFAULT_PERSONAS.copy()
    
    # Step 1: Run all personas in parallel
    results = []
    with ThreadPoolExecutor(max_workers=len(personas)) as executor:
        future_to_persona = {
            executor.submit(_run_single_persona, p, topic, user_question): p
            for p in personas
        }
        for future in as_completed(future_to_persona):
            res = future.result()
            results.append(res)
            # Log each agent's response as soon as it arrives
            if player and "error" not in res:
                player.write_log(f"[Agent {res['role']}]\n{res['response']}\n")
            elif player:
                player.write_log(f"[Agent {res['persona']}] Error: {res.get('error', 'Unknown')}")
    
    if player:
        player.write_log(f"[DISCUSS] Collected {len(results)} perspectives.")
    
    # Step 2: Synthesise
    synthesis = _synthesize(results, topic, user_question)
    
    if two_rounds:
        # Step 3: Refinement round
        if player:
            player.write_log("[DISCUSS] Second round: critique & refinement...")
        final = _second_round_refinement(synthesis, results, topic)
    else:
        final = synthesis
    
    # Speak the final answer
    if speak:
        speak(final)
    
    if player:
        player.write_log("[DISCUSS] Discussion complete.")
    
    return final

# Convenience function to be used as a tool by main.py
def discuss_topic_tool(parameters: dict, player=None, speak=None) -> str:
    """
    Tool interface compatible with code_helper and main.py.
    Expected parameters:
        topic: str (required)
        question: str (optional)
        personas: list (optional, e.g., ["logical","creative"])
        rounds: int (1 or 2, default 2)
    """
    topic = parameters.get("topic", "")
    if not topic:
        topic = parameters.get("description", "")
    if not topic:
        return "Please provide a topic to discuss."
    
    user_q = parameters.get("question", "")
    personas = parameters.get("personas")
    two_rounds = parameters.get("rounds", 2) == 2
    
    return discuss_topic(topic, user_q, personas, two_rounds, player, speak)