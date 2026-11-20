import os
import json
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# --- Pydantic Schemas for Structured LLM Output ---
class ExtractedDecision(BaseModel):
    decision_text: str = Field(description="Clear statement of what was decided.")
    context_quote: str = Field(description="Exact quote from transcript proving this decision.")

class ExtractedTask(BaseModel):
    title: str = Field(description="Short actionable task title.")
    description: str = Field(description="Detailed context of what needs to be done.")
    assignee_name: Optional[str] = Field(description="Exact name of the person responsible, or null if unclear.")
    priority: str = Field(description="LOW, MEDIUM, HIGH, or CRITICAL")
    due_date_iso: Optional[str] = Field(description="ISO 8601 date string (YYYY-MM-DDTHH:MM:SS) if a clear deadline is stated, else null.")
    confidence_score: float = Field(description="0.0 to 1.0 confidence that this is a firm commitment with clear owner & deadline.")
    ambiguity_reason: Optional[str] = Field(description="If owner or deadline is missing/vague, explain what needs clarification. Else null.")
    ai_reasoning: str = Field(description="Explain WHY this was classified as an actionable commitment vs casual talk.")
    updates_existing_task_id: Optional[str] = Field(description="If this updates an existing open task provided in context, put its UUID here. Else null.")

class MeetingAnalysis(BaseModel):
    summary: str = Field(description="2-3 sentence executive summary of the meeting.")
    decisions: List[ExtractedDecision]
    tasks: List[ExtractedTask]

def analyze_transcript(transcript: str, team_members: list, existing_tasks: list, current_date: str) -> dict:
    prompt = f"""
    You are an autonomous Meeting-to-Action AI Agent. Analyze the meeting transcript below.
    Current Date/Time: {current_date}

    TEAM MEMBERS (Map assignees to these exact names if mentioned):
    {json.dumps(team_members)}

    EXISTING OPEN TASKS FROM PREVIOUS MEETINGS (Check if the transcript mentions progress/updates on these instead of creating duplicates):
    {json.dumps(existing_tasks)}

    INSTRUCTIONS:
    1. Distinguish firm commitments from casual ideas or brainstorming.
    2. Extract key decisions with exact transcript quotes.
    3. Extract actionable tasks. If an owner or deadline is missing or vague (e.g., "soon", "next week"), set confidence_score < 0.75 and explain what is ambiguous in 'ambiguity_reason'.
    4. Always provide 'ai_reasoning' explaining your decision-making logic.

    TRANSCRIPT:
    {transcript}
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=MeetingAnalysis,
            temperature=0.1,
        ),
    )
    return json.loads(response.text)