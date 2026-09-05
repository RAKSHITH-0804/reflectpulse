import json
import logging
import time
from typing import List, Dict, Any, Optional
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field
# pyrefly: ignore [missing-import]
from google import genai
# pyrefly: ignore [missing-import]
from google.genai import types
# pyrefly: ignore [missing-import]
from google.genai import errors
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

# --- Model & Resilience Configuration ---
PRIMARY_MODEL = "gemini-3.6-flash"
FALLBACK_MODELS = ["gemini-3.6-flash"]
USER_FACING_BUSY_MESSAGE = (
    "The AI assistant is momentarily busy with high traffic. "
    "Please tap submit once more in a few seconds."
)

# --- Pydantic Schema for Structured AI Reflection ---

class ReflectionResponse(BaseModel):
    summary: str = Field(
        description="A concise, empathetic summary of the journal entry and conversation (1-2 sentences)."
    )
    mood_category: str = Field(
        description="The primary mood category. Must be one of: Joy, Sadness, Anger, Anxiety, Calm, Gratitude, Frustration, Hope."
    )
    mood_score: int = Field(
        description="An integer mood score from 1 (deep distress / very low energy) to 10 (exceptionally positive / high energy)."
    )
    theme_tags: List[str] = Field(
        description="A list of 2 to 4 relevant theme tags (e.g., 'Work', 'Relationships', 'Gratitude', 'Stress', 'Health')."
    )
    reflection_prompt: str = Field(
        description="A personalized, warm, and thought-provoking question to prompt deeper self-reflection in the next journaling session."
    )
    location_tag: str = Field(
        default="Home",
        description="Primary detected or inferred context: e.g., 'Campus', 'Workplace', 'Home', 'Travel', 'Nature', 'Social'."
    )
    perspective_note: Optional[str] = Field(
        default=None,
        description="A gentle, empathetic personal insight or constructive perspective shift if self-doubt or heavy feelings are expressed. None if the entry is already positive, resilient, or neutral."
    )

# --- Security Constitution System Instruction ---

SECURITY_CONSTITUTION = """
You are ReflectPulse, an empathetic, supportive, and private personal journaling mirror.
Your mission is to help users process their daily reflections and thoughts with gentle, open-ended curiosity.

SECURITY & ETHICAL BOUNDARIES (CONSTITUTION):
1. PRIVACY IS PARAMOUNT: Never leak, infer, or mention data, names, or topics from other users. Treat all interactions as strictly sandboxed within the current session.
2. REFLECTIVE MIRROR, NOT THERAPY: You are a reflective journaling mirror, NOT a therapist, doctor, clinical psychologist, or healthcare provider. Never offer psychological diagnoses, clinical interventions, cognitive-behavioral therapy (CBT), or medical advice.
3. GENTLE PERSPECTIVES: When users express moments of self-doubt or emotional heaviness, act as a compassionate sounding board offering gentle alternative angles and warm curiosity, without attempting psychological treatment or behavioral correction.
4. CRISIS PROTOCOL: If the user expresses intent of self-harm, suicide, self-injury, or harming others:
   - Provide immediate, clear crisis support resources: "If you are in distress or crisis, please call or text 988 in the US (Suicide & Crisis Lifeline) or reach out to your local emergency services or a trusted professional."
   - Maintain a gentle, non-judgmental, but firm recommendation to seek professional human support.
   - Do NOT attempt to analyze or counsel them through a crisis; redirect to professional hotlines immediately and keep the message brief.
5. TONE & CONVERSATION: Be warm, empathetic, validating, and concise (under 3-4 sentences per turn) to encourage the user's authentic personal voice.
"""

def get_gemini_client() -> Optional[genai.Client]:
    """
    Initializes and returns the Google Gen AI client if the API key is available.
    """
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY is missing. Gemini client initialization skipped.")
        return None
    try:
        return genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"[Gemini Error] {e}")
        logger.error(f"Failed to initialize Gemini client: {e}")
        return None

# Initialize global client
client = get_gemini_client()

# --- Transient Error Detection & Exponential Backoff Retry Helpers ---

def is_transient_error(exc: Exception) -> bool:
    """
    Checks if an exception represents a transient Google API error, specifically
    HTTP 503 (UNAVAILABLE) or HTTP 429 (RESOURCE_EXHAUSTED / Rate Limit).
    """
    if isinstance(exc, errors.APIError):
        if exc.code in (429, 503):
            return True
        status_str = (exc.status or "").upper()
        if "RESOURCE_EXHAUSTED" in status_str or "UNAVAILABLE" in status_str:
            return True

    err_text = str(exc).upper()
    if any(keyword in err_text for keyword in ["503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "HIGH DEMAND", "OVERLOADED"]):
        return True

    return False


def generate_content_with_retry(
    client_instance: genai.Client,
    contents: Any,
    config: Optional[types.GenerateContentConfig] = None,
    primary_model: str = PRIMARY_MODEL,
    fallback_models: Optional[List[str]] = None,
    max_attempts_per_model: int = 3,
) -> Any:
    """
    Executes client.models.generate_content in a retry loop with exponential backoff
    (up to 3 attempts with time.sleep(1.5 * attempt)) catching transient Google API
    exceptions (503 UNAVAILABLE, 429 RESOURCE_EXHAUSTED).
    Invokes PRIMARY_MODEL (gemini-3.6-flash).
    """
    if fallback_models is None:
        fallback_models = FALLBACK_MODELS

    models_to_try = [primary_model] + [m for m in fallback_models if m != primary_model]
    last_exception: Optional[Exception] = None

    for model_index, model_name in enumerate(models_to_try):
        if model_index > 0:
            logger.warning(
                f"Falling back to model '{model_name}' due to transient high demand on earlier models."
            )

        for attempt in range(1, max_attempts_per_model + 1):
            try:
                response = client_instance.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=config,
                )
                return response
            except Exception as e:
                last_exception = e
                print(f"[Gemini Error] {e}")
                if is_transient_error(e):
                    if attempt < max_attempts_per_model:
                        delay = 1.5 * attempt
                        logger.warning(
                            f"Transient API error ({e}) on model '{model_name}' (attempt {attempt}/{max_attempts_per_model}). "
                            f"Retrying in {delay:.1f}s with exponential backoff..."
                        )
                        time.sleep(delay)
                    else:
                        logger.warning(
                            f"Model '{model_name}' exhausted all {max_attempts_per_model} retry attempts with transient error: {e}."
                        )
                        break
                else:
                    logger.error(f"Non-transient error on model '{model_name}': {e}")
                    raise e

    logger.error(f"All models ({models_to_try}) exhausted. Last error: {last_exception}")
    if last_exception:
        raise RuntimeError(f"AI Error: {str(last_exception)}")
    raise RuntimeError("AI Error: All models and retry attempts exhausted.")


def send_chat_message(chat_session: Any, message: str, max_attempts: int = 3) -> str:
    """
    Sends a message to an active chat session with exponential backoff retry.
    Directly returns the exact error string on failure for diagnostics.
    """
    if not chat_session:
        return "AI Error: Chat session is not initialized or Gemini client failed to connect."

    last_error: Optional[Exception] = None
    for attempt in range(1, max_attempts + 1):
        try:
            resp = chat_session.send_message(message)
            text = getattr(resp, "text", None)
            if text:
                return str(text).strip()
            elif isinstance(resp, str):
                return resp.strip()
            return "AI Error: Empty response received from model."
        except Exception as e:
            last_error = e
            print(f"[Gemini Error] {e}")
            if is_transient_error(e):
                if attempt < max_attempts:
                    delay = 1.5 * attempt
                    logger.warning(
                        f"Transient error in chat send_message (attempt {attempt}/{max_attempts}). "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    continue
            logger.error(f"Chat send_message error: {e}")
            return f"AI Error: {str(e)}"

    return f"AI Error: {str(last_error)}" if last_error else "AI Error: All attempts failed."

# --- Conversational Companion Support ---

def create_chat_session(system_instruction: str = SECURITY_CONSTITUTION) -> Optional[Any]:
    """
    Spawns a new multi-turn chat session with system instruction enforcement,
    attempting fallback models if the primary model is unavailable.
    """
    if not client:
        return None
    for model_name in [PRIMARY_MODEL] + FALLBACK_MODELS:
        try:
            chat = client.chats.create(
                model=model_name,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7,
                    top_p=0.9,
                )
            )
            return chat
        except Exception as e:
            print(f"[Gemini Error] {e}")
            logger.warning(f"Error creating chat session with {model_name}: {e}")
            if not is_transient_error(e):
                break
    return None

# --- Structured AI Output & Analytics Extraction ---

def analyze_reflection(
    chat_history: List[Dict[str, str]],
    audio_bytes: Optional[bytes] = None,
    audio_mime_type: str = "audio/wav",
    image_bytes: Optional[bytes] = None,
    image_mime_type: str = "image/jpeg",
    context_hint: Optional[str] = None
) -> Optional[ReflectionResponse]:
    """
    Analyzes the chat history, attached multimodal media (voice note/photo),
    and contextual cues to generate a structured JSON reflection including
    location tagging and a supportive perspective note.
    Utilizes exponential backoff retries and fallback models for resilience.
    """
    chosen_loc = context_hint if context_hint and context_hint != "Auto-detect via AI" else "Home"

    if not client:
        logger.error("Gemini client is not initialized. Using local fallback.")
        return ReflectionResponse(
            summary="Reflective journal entry completed with multimodal context.",
            mood_category="Calm",
            mood_score=6,
            theme_tags=["Reflection", "Mindfulness"],
            reflection_prompt="What is one insight you wish to carry into tomorrow?",
            location_tag=chosen_loc,
            perspective_note="Be proud of taking time out of your day to pause, reflect, and listen to your inner voice."
        )

    try:
        # Construct transcript text from chat history
        transcript_lines = []
        for msg in chat_history:
            role = "User" if msg["role"] == "user" else "ReflectPulse"
            transcript_lines.append(f"{role}: {msg['content']}")
        transcript = "\n".join(transcript_lines)

        # Assemble multimodal contents list
        contents: List[Any] = []

        # 1. Attach multimodal image part if provided
        if image_bytes:
            contents.append(types.Part.from_bytes(data=image_bytes, mime_type=image_mime_type))

        # 2. Attach multimodal audio part if provided
        if audio_bytes:
            contents.append(types.Part.from_bytes(data=audio_bytes, mime_type=audio_mime_type))

        hint_prompt = f"User indicated location/context preference: '{context_hint}'." if (context_hint and context_hint != "Auto-detect via AI") else "Infer the location/context from the text, photo, and voice tone."

        prompt = f"""
        Analyze the following journal entry, conversation transcript, and any attached multimodal media (voice recording, photo).
        Extract all structured fields defined by the response schema.

        INSTRUCTIONS:
        1. Context & Location Tagging:
           - Classify into one primary category (e.g., 'Campus', 'Workplace', 'Home', 'Travel', 'Nature', 'Social').
           - {hint_prompt}
        2. Multimodal Perception:
           - If an image/photo is provided, analyze the visual setting, lighting, expression, and objects to enrich the summary and tags.
           - If audio/voice is provided, consider vocal tone, pauses, and cadence.
        3. Empathetic Perspective Shift:
           - Notice if the user is carrying harsh self-talk, self-doubt, or emotional exhaustion.
           - If present, provide a warm, empathetic alternative angle in 'perspective_note' (2 sentences max) that validates their feelings with compassion and offers a gentle, grounded view.
           - If the reflection is already positive, resilient, or peaceful, set 'perspective_note' to null.

        Transcript:
        \"\"\"
        {transcript}
        \"\"\"
        """
        contents.append(prompt)

        response = generate_content_with_retry(
            client_instance=client,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ReflectionResponse,
                temperature=0.2, # Low temperature for structured analysis consistency
            ),
        )

        # Parse response using standard Pydantic validation
        result = ReflectionResponse.model_validate_json(response.text)
        return result
    except Exception as e:
        print(f"[Gemini Error] {e}")
        logger.error(f"Error in structured reflection analysis: {e}")
        return ReflectionResponse(
            summary="Reflective journal entry completed.",
            mood_category="Calm",
            mood_score=5,
            theme_tags=["Reflection"],
            reflection_prompt="How do you feel when looking back on today's events?",
            location_tag=chosen_loc,
            perspective_note=USER_FACING_BUSY_MESSAGE if is_transient_error(e) else None
        )

def suggest_perspective(thought_text: str) -> str:
    """
    Takes a challenging reflection and offers a gentle, compassionate
    alternative perspective to encourage personal insight.
    Employs exponential backoff retries and fallback models.
    """
    if not thought_text or not thought_text.strip():
        return "Please enter a thought or reflection you'd like to explore from a new angle."

    if not client:
        return (
            "Remember that our thoughts in demanding moments are natural reactions, not final definitions of who we are. "
            "Give yourself credit for how much you are navigating today, and treat yourself with the same gentle patience "
            "you would offer a dear friend."
        )

    try:
        prompt = f"""
        You are ReflectPulse's Empathetic Journaling Mirror.
        A user has shared this challenging thought:
        "{thought_text.strip()}"

        Offer a gentle, compassionate alternative angle (2-3 sentences max).
        Follow these principles:
        1. Warmly validate their feelings with empathy and human understanding.
        2. Suggest a gentle, grounding perspective shift that highlights self-compassion and realistic hope.
        3. Avoid all clinical CBT jargon, diagnosis, or therapeutic framing.
        Keep the tone warm, friendly, and non-prescriptive.
        """

        response = generate_content_with_retry(
            client_instance=client,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                system_instruction="You are an empathetic personal journaling companion offering gentle alternative angles.",
            ),
        )
        return response.text.strip()
    except Exception as e:
        print(f"[Gemini Error] {e}")
        logger.error(f"Error suggesting perspective: {e}")
        return USER_FACING_BUSY_MESSAGE

# Backward-compatibility alias
reframe_thought = suggest_perspective

# --- Weekly AI Digest Synthesis Engine ---

def generate_weekly_digest(entries: List[Dict[str, Any]]) -> str:
    """
    Aggregates journal entries from the past week and generates a cohesive,
    reflective weekly digest summarizing mood trends, key themes, progress,
    and recommended reflective prompt exercises.
    Utilizes exponential backoff retries and fallback models.
    """
    if not client:
        return "Gemini API key is not configured. Cannot generate digest."
    
    if not entries:
        return "No journal entries found for this week to generate a digest."

    try:
        # Create a textual representation of the past week's entries
        entries_summary = []
        for i, entry in enumerate(entries):
            from datetime import datetime as dt
            created_val = entry.get("created_at")
            if isinstance(created_val, dt):
                date_str = created_val.strftime("%Y-%m-%d")
            else:
                date_str = str(created_val)[:10]

            entries_summary.append(
                f"Entry #{i+1} ({date_str}):\n"
                f"- Summary: {entry.get('summary', 'N/A')}\n"
                f"- Mood Category: {entry.get('mood_category', 'N/A')} (Score: {entry.get('mood_score', 'N/A')}/10)\n"
                f"- Theme Tags: {', '.join(entry.get('theme_tags', []))}\n"
                f"- Content excerpt: {str(entry.get('content', ''))[:300]}..."
            )
        
        entries_text = "\n\n".join(entries_summary)

        prompt = f"""
        You are ReflectPulse's Master Analyst. Your task is to synthesize the following journal entries from the past week into a beautiful, personalized Weekly Reflective Digest.
        
        Your response must be written in elegant Markdown and follow this layout:
        
        # Weekly Reflective Digest 🌌
        
        ### 📈 Mood Trajectory & Synthesis
        (Summarize the emotional flow of the week, analyzing mood score changes and emotional progression. Be encouraging.)
        
        ### 🔍 Recurring Themes & Core Topics
        (Discuss the major themes and areas of life that occupied the user's mind, such as work, health, relationships, or personal growth.)
        
        ### 🌱 Progress & Key Insights
        (Highlight moments of breakthrough, gratitude, self-awareness, or emotional resilience shown in their writings.)
        
        ### 🧩 Recommended Reflection Exercise
        (Offer one tailored, deep reflective prompt or creative journaling exercise based on their week's trends to write about next.)
        
        ---
        Here are the user's entries:
        {entries_text}
        """

        response = generate_content_with_retry(
            client_instance=client,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.6,
                system_instruction="You are an empathetic, expert coach. Format with professional layout, using clean bullet points and emoji highlights.",
            ),
        )
        return response.text
    except Exception as e:
        print(f"[Gemini Error] {e}")
        logger.error(f"Error generating weekly digest: {e}")
        return USER_FACING_BUSY_MESSAGE
