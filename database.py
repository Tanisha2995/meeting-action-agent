import os
import uuid
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Text, Float, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

database_url = os.getenv("DATABASE_URL", "")
if not database_url or "YOUR-" in database_url:
    database_url = "sqlite:///meeting_action.db"

if database_url.startswith("sqlite"):
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
else:
    engine = create_engine(database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    role = Column(String(100))

class Meeting(Base):
    __tablename__ = "meetings"
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    meeting_date = Column(DateTime, default=datetime.utcnow)
    raw_transcript = Column(Text, nullable=False)
    summary = Column(Text)

class Decision(Base):
    __tablename__ = "decisions"
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(Uuid(as_uuid=True), ForeignKey("meetings.id"))
    decision_text = Column(Text, nullable=False)
    context_quote = Column(Text)

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(Uuid(as_uuid=True), ForeignKey("meetings.id"))
    assignee_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    priority = Column(String(20), default="MEDIUM")
    status = Column(String(50), default="NEEDS_CONFIRMATION")
    due_date = Column(DateTime, nullable=True)
    confidence_score = Column(Float)
    ambiguity_reason = Column(Text, nullable=True)
    ai_reasoning = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class FollowUp(Base):
    __tablename__ = "follow_ups"
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(Uuid(as_uuid=True), ForeignKey("tasks.id"))
    message = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


Base.metadata.create_all(engine)