
import OpenAI from "openai";
import dotenv from "dotenv";

dotenv.config({ path: "../.env" });

const client = new OpenAI({
  apiKey: process.env.BLUESMINDS_API_KEY,
  baseURL: process.env.BLUESMINDS_BASE_URL
});

export const extractMeetingActions = async (transcript) => {
  if (!transcript || typeof transcript !== "string") {
    throw new Error("A valid meeting transcript is required");
  }

  const response = await client.chat.completions.create({
    model: process.env.BLUESMINDS_MODEL,

    messages: [
      {
        role: "system",
        content: `
You are an intelligent AI meeting assistant.

Analyze meeting transcripts and extract actionable information.

Return ONLY valid JSON in this structure:

{
  "summary": "Meeting summary",
  "tasks": [
  {
    "title": "Task title",
    "description": "Task details",
    "required_skills": ["React", "JavaScript", "UI design"],
    "assignee": null,
    "priority": "high",
    "status": "pending",
    "due_date": null,
    "confidence_score": 0.95,
    "ambiguity_reason": null,
    "ai_reasoning": "Reason for extracting this task"
  }
]
  "decisions": [
    {
      "decision_text": "Decision made",
      "context_quote": "Exact supporting transcript quote"
    }
  ]
}

STRICT RULES:

1. Never invent tasks, names or deadlines.
2. Only assign a person when the transcript clearly identifies them.
3. Priority must be high, medium or low.
4. Status must always be pending for newly extracted tasks.
5. Confidence score must be between 0 and 1.
6. Use null for unknown values.
7. Dates must use YYYY-MM-DD format.
8. If a deadline is ambiguous, use null and explain why.
9. Extract only actual decisions, not suggestions.
10. Return empty arrays when no tasks or decisions exist.
11. Identify the technical or functional skills required for each task.
12. Return required_skills as an array of skill names.
13. Never invent an assignee when the meeting does not identify one.
`
      },
      {
        role: "user",
        content: `Analyze this meeting transcript:\n\n${transcript}`
      }
    ],

    response_format: {
      type: "json_object"
    }
  });

  const content = response.choices[0].message.content;

  if (!content) {
    throw new Error("AI returned an empty response");
  }

  const result = JSON.parse(content);

  if (
    typeof result.summary !== "string" ||
    !Array.isArray(result.tasks) ||
    !Array.isArray(result.decisions)
  ) {
    throw new Error("AI returned an invalid extraction structure");
  }

  return result;
};

