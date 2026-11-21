
import os
import json
from pathlib import Path
from typing import List, Optional

from openai import OpenAI
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load the root .env file
load_dotenv(Path(__file__).resolve().parent / ".env")

api_key = os.getenv("BLUESMINDS_API_KEY")
base_url = os.getenv("BLUESMINDS_BASE_URL")
model_name = os.getenv("BLUESMINDS_MODEL")

if not api_key or not base_url or not model_name:
    raise RuntimeError(
        "Missing BluesMinds configuration. "
        "Check BLUESMINDS_API_KEY, BLUESMINDS_BASE_URL "
        "and BLUESMINDS_MODEL in your .env file."
    )

# Connect to BluesMinds using its OpenAI-compatible API
client = OpenAI(
    api_key=api_key,
    base_url=base_url
)


# ---------- Pydantic Schemas ----------

class ExtractedDecision(BaseModel):
    decision_text: str
    context_quote: str


class ExtractedTask(BaseModel):
    title: str
    description: str
    assignee_name: Optional[str] = None
    priority: str = "MEDIUM"
    due_date_iso: Optional[str] = None
    required_skills: List[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0)
    ambiguity_reason: Optional[str] = None
    ai_reasoning: str
    updates_existing_task_id: Optional[str] = None


class MeetingAnalysis(BaseModel):
    summary: str
    decisions: List[ExtractedDecision] = Field(default_factory=list)
    tasks: List[ExtractedTask] = Field(default_factory=list)


# ---------- Meeting Analysis ----------

def analyze_transcript(
    transcript: str,
    team_members: list,
    existing_tasks: list,
    current_date: str
) -> dict:

    if not transcript or not transcript.strip():
        raise ValueError("A valid meeting transcript is required.")

    prompt = f"""
You are an intelligent Meeting-to-Action AI Agent.

CURRENT DATE/TIME:
{current_date}

TEAM MEMBERS:
{json.dumps(team_members, default=str)}

EXISTING OPEN TASKS:
{json.dumps(existing_tasks, default=str)}

Analyze the meeting transcript and return JSON with exactly three top-level fields:

- summary: A concise summary of the actual meeting.
- decisions: An array of decisions, each containing decision_text and context_quote.
- tasks: An array of actionable tasks.

Each task must contain:
title, description, assignee_name, priority, due_date_iso,
required_skills, confidence_score, ambiguity_reason,
ai_reasoning, updates_existing_task_id.

STRICT RULES:

1. Always return summary, decisions and tasks, even when arrays are empty.
2. Keep decisions and tasks in separate arrays.
3. Every decision must have an exact verbatim context_quote from the transcript.
4. Never invent quotes, tasks, people, deadlines or decisions.
5. Extract firm commitments, not suggestions.
6. Assign owners only when explicitly identifiable.
7. Explain missing or uncertain owners/deadlines in ambiguity_reason.
8. Keep confidence below 0.75 when essential information is ambiguous.
9. Priority must be LOW, MEDIUM, HIGH or CRITICAL.
10. Extract relevant skills or use an empty array.
11. Dates must use ISO 8601 format.
12. Use null for unknown owners and deadlines.
13. Confidence must be between 0 and 1.
14. Check existing tasks before creating duplicates.
15. Include an existing task UUID when updating a task.
16. Explain the evidence for each commitment in ai_reasoning.
17. Summary must never be empty when the transcript contains meeting information.
18. Return valid JSON only, without Markdown or commentary.


TRANSCRIPT:
{transcript}
"""

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise meeting intelligence assistant. "
                    "Return only valid JSON matching the requested structure."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format={"type": "json_object"},
        temperature=0.1
    )

    
    content = response.choices[0].message.content

    if not content:
        raise RuntimeError("BluesMinds returned an empty response.")

    raw = json.loads(content)

    # Normalize the model's field names into our application schema
    raw_tasks = raw.get("tasks", []) or []
    decisions = raw.get("decisions", []) or []
    tasks = []

    for item in raw_tasks:
        # The model sometimes puts decisions inside the tasks array
        if item.get("decision_id"):
            decisions.append(item)
            continue

        title = item.get("title") or item.get("description") or "Untitled task"

        priority = str(item.get("priority") or "MEDIUM").upper()
        if priority not in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
            priority = "MEDIUM"

        tasks.append({
            "title": title,
            "description": item.get("description") or title,
            "assignee_name": item.get("assignee_name") or item.get("assignee"),
            "priority": priority,
            "due_date_iso": item.get("due_date_iso") or item.get("deadline"),
            "required_skills": item.get("required_skills") or [],
            "confidence_score": item.get("confidence_score", 0.5),
            "ambiguity_reason": item.get("ambiguity_reason"),
            "ai_reasoning": item.get("ai_reasoning") or "",
            "updates_existing_task_id": item.get("updates_existing_task_id")
        })

    normalized_decisions = []

    for item in decisions:
        normalized_decisions.append({
            "decision_text": item.get("decision_text") or item.get("description") or "",
            "context_quote": item.get("context_quote") or item.get("decision_quote") or ""
        })

    normalized = {
        "summary": raw.get("summary") or "Summary unavailable from AI response.",
        "decisions": normalized_decisions,
        "tasks": tasks
    }

    result = MeetingAnalysis.model_validate(normalized)

    return result.model_dump(mode="json")

    if not content:
        raise RuntimeError("BluesMinds returned an empty response.")

    # Validate the returned JSON against our schemas
    print("RAW BLUESMINDS RESPONSE:")
    print(content)
    result = MeetingAnalysis.model_validate_json(content)

   