import json
import logging
from typing import List, Dict, Any, Optional
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field
# pyrefly: ignore [missing-import]
from google import genai
# pyrefly: ignore [missing-import]
from google.genai import types
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

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
    cognitive_reframe: Optional[str] = Field(
        default=None,
        description="A gentle, non-clinical constructive reframe if negative self-talk, self-doubt, or cognitive distortions are detected in the entry. None if the entry is already positive or neutral."
    )

# --- Security Constitution System Instruction ---

SECURITY_CONSTITUTION = """
You are ReflectPulse, an empathetic, supportive, and private AI journaling companion.
Your mission is to guide users through self-reflection and help them process their thoughts.

SECURITY & ETHICAL BOUNDARIES (CONSTITUTION):
1. PRIVACY IS PARAMOUNT: Never leak, infer, or mention data, names, or topics from other users. Treat all interactions as strictly sandboxed within the current session.
2. SUPPORTIVE BUT NOT THERAPEUTIC: You are a journal companion, NOT a certified therapist, doctor, or psychologist. Do not diagnose mental health conditions, prescribe treatments, or offer clinical advice.
3. CRISIS PROTOCOL & SELF-HARM DETECTOR: If the user expresses intent of self-harm, suicide, self-injury, or harming others:
   - Provide immediate, clear crisis support resources: "If you are in distress or crisis, please call or text 988 in the US (Suicide & Crisis Lifeline) or reach out to your local emergency services or a trusted professional."
   - Maintain a gentle, non-judgmental, but firm recommendation to seek professional help.
   - Do NOT attempt to analyze or solve their crisis; redirect to professional hotlines immediately and keep the message brief.
4. TONE & CONVERSATION: Be warm, active-listening, encouraging, and reflective. Keep chat responses concise (under 3-4 sentences per turn) to encourage the user to write more.
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
        logger.error(f"Failed to initialize Gemini client: {e}")
        return None

# Initialize global client
client = get_gemini_client()

# --- Conversational Companion Support ---

def create_chat_session(system_instruction: str = SECURITY_CONSTITUTION) -> Optional[Any]:
    """
    Spawns a new multi-turn chat session with system instruction enforcement.
    """
    if not client:
        return None
    try:
        # Using gemini-3.6-flash as the default model
        chat = client.chats.create(
            model="gemini-3.6-flash",
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
                top_p=0.9,
            )
        )
        return chat
    except Exception as e:
        logger.error(f"Error creating chat session: {e}")
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
    location tagging and cognitive reframing.
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
            cognitive_reframe="Be proud of taking time out of your day to pause, reflect, and listen to your inner voice."
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
        3. Cognitive Reframing:
           - Detect any negative self-talk, impostor syndrome, catastrophizing, or harsh self-criticism.
           - If present, provide a gentle, non-clinical constructive reframe in 'cognitive_reframe' that validates feelings while offering a balanced, self-compassionate view.
           - If the reflection is already positive, resilient, or neutral, set 'cognitive_reframe' to null.

        Transcript:
        \"\"\"
        {transcript}
        \"\"\"
        """
        contents.append(prompt)

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ReflectionResponse,
                temperature=0.2, # Low temperature for structured analysis consistency
            )
        )

        # Parse response using standard Pydantic validation
        result = ReflectionResponse.model_validate_json(response.text)
        return result
    except Exception as e:
        logger.error(f"Error in structured reflection analysis: {e}")
        return ReflectionResponse(
            summary="Reflective journal entry completed.",
            mood_category="Calm",
            mood_score=5,
            theme_tags=["Reflection"],
            reflection_prompt="How do you feel when looking back on today's events?",
            location_tag=chosen_loc,
            cognitive_reframe=None
        )

def reframe_thought(thought_text: str) -> str:
    """
    Takes a self-critical thought or cognitive distortion and generates
    a gentle, non-clinical constructive reframe to power the quick-reframe widget.
    """
    if not thought_text or not thought_text.strip():
        return "Please enter a thought you would like to reframe."

    if not client:
        return (
            "Remember that feelings are experiences, not permanent definitions of who you are. "
            "Give yourself credit for how much you are navigating, and treat yourself with the same compassion "
            "you would extend to a trusted friend."
        )

    try:
        prompt = f"""
        You are ReflectPulse's Cognitive Reframing Guide.
        A user has shared this challenging or self-critical thought:
        "{thought_text.strip()}"

        Provide a gentle, empathetic, and constructive non-clinical cognitive reframe (2-3 sentences max).
        Follow these principles:
        1. Validate their underlying emotional experience without endorsing distorted self-talk.
        2. Offer an alternative, compassionate, and realistic perspective.
        3. End with an empowering, grounding insight.
        Do NOT sound clinical or diagnostic. Keep the tone warm, conversational, and uplifting.
        """

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                system_instruction="You are an empathetic companion specializing in gentle cognitive reframing.",
            )
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error reframing thought: {e}")
        return f"Could not reframe thought at this moment: {e}"

# --- Weekly AI Digest Synthesis Engine ---

def generate_weekly_digest(entries: List[Dict[str, Any]]) -> str:
    """
    Aggregates journal entries from the past week and generates a cohesive,
    reflective weekly digest summarizing mood trends, key themes, progress,
    and recommended reflective prompt exercises.
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

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.6,
                system_instruction="You are an empathetic, expert coach. Format with professional layout, using clean bullet points and emoji highlights.",
            )
        )
        return response.text
    except Exception as e:
        logger.error(f"Error generating weekly digest: {e}")
        return f"An error occurred while synthesizing your weekly digest: {e}"
