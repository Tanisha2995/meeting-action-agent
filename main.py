import os
import requests
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, User, Meeting, Decision, Task, FollowUp
from agent import analyze_transcript

app = FastAPI(title="Meeting-to-Action AI Agent API")

# Allow frontend to connect from anywhere during hackathon
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Request Schemas ---
class IngestRequest(BaseModel):
    title: str
    transcript: str

class ConfirmTaskRequest(BaseModel):
    assignee_id: Optional[UUID] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = None

class StatusUpdateRequest(BaseModel):
    status: str # 'OPEN', 'IN_PROGRESS', 'COMPLETED'


def parse_due_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    except ValueError:
        return None

# --- Helper: Send Webhook Notification ---
def send_notification(message: str):
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if webhook_url:
        try:
            requests.post(webhook_url, json={"content": message}, timeout=5)
        except Exception as e:
            print("Webhook error:", e)

# --- 1. Ingest Meeting & Run AI Agent ---
@app.post("/api/meetings/ingest")
def ingest_meeting(req: IngestRequest, db: Session = Depends(get_db)):
    users = db.query(User).all()
    team_context = [{"id": str(u.id), "name": u.name, "role": u.role} for u in users]
    user_map = {u.name.lower(): u.id for u in users}

    open_tasks = db.query(Task).filter(Task.status != "COMPLETED").all()
    tasks_context = [{"id": str(t.id), "title": t.title, "status": t.status} for t in open_tasks]

    # Run AI Agent
    analysis = analyze_transcript(
        transcript=req.transcript,
        team_members=team_context,
        existing_tasks=tasks_context,
        current_date=datetime.utcnow().isoformat()
    )

    # Save Meeting
    meeting = Meeting(title=req.title, raw_transcript=req.transcript, summary=analysis["summary"])
    db.add(meeting)
    db.commit()
    db.refresh(meeting)

    # Save Decisions
    for d in analysis["decisions"]:
        db.add(Decision(meeting_id=meeting.id, decision_text=d["decision_text"], context_quote=d["context_quote"]))

    # Save or Update Tasks
    created_tasks = []
    for t in analysis["tasks"]:
        # Cross-meeting check: update existing task if matched
        if t.get("updates_existing_task_id"):
            try:
                existing_task_id = UUID(t["updates_existing_task_id"])
            except (ValueError, TypeError, AttributeError):
                existing_task_id = None
            existing = db.query(Task).filter(Task.id == existing_task_id).first() if existing_task_id else None
            if existing:
                existing.ai_reasoning = (existing.ai_reasoning or "") + f" | Update from '{req.title}': {t['ai_reasoning']}"
                assignee_id = user_map.get(t["assignee_name"].lower()) if t.get("assignee_name") else existing.assignee_id
                if assignee_id:
                    existing.assignee_id = assignee_id
                existing.due_date = parse_due_date(t.get("due_date_iso")) or existing.due_date
                existing.priority = t.get("priority") or existing.priority
                continue

        assignee_id = user_map.get(t["assignee_name"].lower()) if t.get("assignee_name") else None
        due_date = parse_due_date(t.get("due_date_iso"))

        # Human-in-the-Loop trigger rule
        needs_hitl = (assignee_id is None) or (due_date is None) or (t["confidence_score"] < 0.75)
        status = "NEEDS_CONFIRMATION" if needs_hitl else "OPEN"

        new_task = Task(
            meeting_id=meeting.id,
            assignee_id=assignee_id,
            title=t["title"],
            description=t["description"],
            priority=t["priority"],
            status=status,
            due_date=due_date,
            confidence_score=t["confidence_score"],
            ambiguity_reason=t.get("ambiguity_reason"),
            ai_reasoning=t["ai_reasoning"]
        )
        db.add(new_task)
        created_tasks.append(new_task)

    db.commit()
    return {"meeting_id": meeting.id, "summary": meeting.summary, "decisions": analysis["decisions"], "tasks_extracted": len(created_tasks)}

# --- 2. Get All Users ---
@app.get("/api/users")
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()

# --- 3. Get Meeting Details ---
@app.get("/api/meetings/{meeting_id}")
def get_meeting(meeting_id: UUID, db: Session = Depends(get_db)):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    decisions = db.query(Decision).filter(Decision.meeting_id == meeting_id).all()
    tasks = db.query(Task).filter(Task.meeting_id == meeting_id).all()
    return {"meeting": meeting, "decisions": decisions, "tasks": tasks}

# --- 4. Get All Tasks Across Meetings ---
@app.get("/api/tasks")
def list_tasks(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Task)
    if status:
        query = query.filter(Task.status == status)
    return query.order_by(Task.created_at.desc()).all()

# --- 5. Human-in-the-Loop Confirmation ---
@app.patch("/api/tasks/{task_id}/confirm")
def confirm_task(task_id: UUID, req: ConfirmTaskRequest, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if req.assignee_id:
        task.assignee_id = req.assignee_id
    if req.due_date:
        task.due_date = req.due_date
    if req.priority:
        task.priority = req.priority
    task.status = "OPEN"
    task.ambiguity_reason = None
    db.commit()
    db.refresh(task)

    send_notification(f"✅ **New Action Item Confirmed:** {task.title} (Priority: {task.priority})")
    return task

# --- 6. Update Task Progress ---
@app.patch("/api/tasks/{task_id}/status")
def update_status(task_id: UUID, req: StatusUpdateRequest, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = req.status
    db.commit()
    return task

# --- 7. Trigger Intelligent Follow-ups (Great for Live Demo!) ---
@app.post("/api/followups/trigger")
def trigger_followups(db: Session = Depends(get_db)):
    pending_tasks = db.query(Task).filter(Task.status.in_(["NEEDS_CONFIRMATION", "OPEN"])).all()
    sent_logs = []

    for task in pending_tasks:
        user = db.query(User).filter(User.id == task.assignee_id).first()
        user_name = user.name if user else "Team"

        if task.status == "NEEDS_CONFIRMATION":
            msg = f"⚠️ **Clarification Needed ({user_name}):** '{task.title}' — {task.ambiguity_reason}"
        elif task.due_date and task.due_date < datetime.utcnow():
            msg = f"🚨 **Overdue Follow-up ({user_name}):** '{task.title}' was due on {task.due_date.strftime('%Y-%m-%d')}."
        else:
            msg = f"🔔 **Reminder ({user_name}):** Please update progress on '{task.title}'."

        send_notification(msg)
        log = FollowUp(task_id=task.id, message=msg)
        db.add(log)
        sent_logs.append(msg)

    db.commit()
    return {"followups_sent": len(sent_logs), "messages": sent_logs}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    