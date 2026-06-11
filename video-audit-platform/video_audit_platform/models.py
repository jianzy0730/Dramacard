from datetime import datetime

from sqlalchemy import inspect as sqlalchemy_inspect, text

from .extensions import db


class StorySeries(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    series_key = db.Column(db.String(120), unique=True, nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    metadata_json = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "series_key": self.series_key,
            "title": self.title,
            "metadata": self.metadata_json or {},
            "created_at": self.created_at.isoformat() + "Z",
            "updated_at": self.updated_at.isoformat() + "Z",
        }


class EpisodeMemory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    series_id = db.Column(db.Integer, db.ForeignKey("story_series.id"), nullable=False, index=True)
    series_key = db.Column(db.String(120), nullable=False, index=True)
    episode_number = db.Column(db.Integer, nullable=False, index=True)
    video_filename = db.Column(db.String(255), nullable=False)
    episode_summary = db.Column(db.Text, nullable=False, default="")
    main_events = db.Column(db.JSON, nullable=False, default=list)
    character_states = db.Column(db.JSON, nullable=False, default=list)
    plot_threads = db.Column(db.JSON, nullable=False, default=list)
    memory_events = db.Column(db.JSON, nullable=False, default=list)
    scene_memories = db.Column(db.JSON, nullable=False, default=list)
    highlights = db.Column(db.JSON, nullable=False, default=list)
    raw_payload = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("series_key", "episode_number", name="uq_episode_memory_series_episode"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "series_key": self.series_key,
            "episode_number": self.episode_number,
            "video_filename": self.video_filename,
            "episode_summary": self.episode_summary,
            "main_events": self.main_events or [],
            "character_states": self.character_states or [],
            "plot_threads": self.plot_threads or [],
            "memory_events": self.memory_events or [],
            "scene_memories": self.scene_memories or [],
            "highlights": self.highlights or [],
            "created_at": self.created_at.isoformat() + "Z",
            "updated_at": self.updated_at.isoformat() + "Z",
        }


class StoryMemoryEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    series_id = db.Column(db.Integer, db.ForeignKey("story_series.id"), nullable=False, index=True)
    series_key = db.Column(db.String(120), nullable=False, index=True)
    episode_id = db.Column(db.Integer, db.ForeignKey("episode_memory.id"), nullable=False, index=True)
    episode_number = db.Column(db.Integer, nullable=False, index=True)
    scene_index = db.Column(db.Integer, nullable=True)
    start_time = db.Column(db.Float, nullable=True)
    end_time = db.Column(db.Float, nullable=True)
    event_key = db.Column(db.String(120), nullable=False, index=True)
    summary = db.Column(db.Text, nullable=False)
    event_type = db.Column(db.String(80), nullable=False, default="other")
    characters = db.Column(db.JSON, nullable=False, default=list)
    payoff_tags = db.Column(db.JSON, nullable=False, default=list)
    plot_thread_key = db.Column(db.String(120), nullable=True, index=True)
    is_open_question = db.Column(db.Boolean, nullable=False, default=False)
    is_resolved = db.Column(db.Boolean, nullable=False, default=False)
    importance = db.Column(db.Integer, nullable=False, default=3)
    metadata_json = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            "event_key": self.event_key,
            "episode_number": self.episode_number,
            "scene_index": self.scene_index,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "summary": self.summary,
            "event_type": self.event_type,
            "characters": self.characters or [],
            "payoff_tags": self.payoff_tags or [],
            "plot_thread_key": self.plot_thread_key,
            "is_open_question": self.is_open_question,
            "is_resolved": self.is_resolved,
            "importance": self.importance,
            "metadata": self.metadata_json or {},
        }


class PlotThreadState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    series_id = db.Column(db.Integer, db.ForeignKey("story_series.id"), nullable=False, index=True)
    series_key = db.Column(db.String(120), nullable=False, index=True)
    episode_id = db.Column(db.Integer, db.ForeignKey("episode_memory.id"), nullable=False, index=True)
    episode_number = db.Column(db.Integer, nullable=False, index=True)
    thread_key = db.Column(db.String(120), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    status = db.Column(db.String(40), nullable=False, default="open")
    priority = db.Column(db.Integer, nullable=False, default=3)
    related_characters = db.Column(db.JSON, nullable=False, default=list)
    source_event_keys = db.Column(db.JSON, nullable=False, default=list)
    last_event_summary = db.Column(db.Text, nullable=True)
    resolution_summary = db.Column(db.Text, nullable=True)
    metadata_json = db.Column(db.JSON, nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            "thread_key": self.thread_key,
            "episode_number": self.episode_number,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "related_characters": self.related_characters or [],
            "source_event_keys": self.source_event_keys or [],
            "last_event_summary": self.last_event_summary,
            "resolution_summary": self.resolution_summary,
            "metadata": self.metadata_json or {},
        }


class AnalysisLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_ip = db.Column(db.String(45), nullable=False)
    video_filename = db.Column(db.String(255), nullable=False)
    series_key = db.Column(db.String(120), nullable=True, index=True)
    episode_number = db.Column(db.Integer, nullable=True, index=True)
    has_violations = db.Column(db.Boolean, default=False, nullable=False)
    report_summary = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_ip": self.user_ip,
            "video_filename": self.video_filename,
            "series_key": self.series_key,
            "episode_number": self.episode_number,
            "has_violations": self.has_violations,
            "report_summary": self.report_summary,
            "timestamp": self.timestamp.isoformat() + "Z",
        }


def ensure_database_schema():
    db.create_all()
    inspector = sqlalchemy_inspect(db.engine)
    table_names = inspector.get_table_names()
    if "analysis_log" not in table_names:
        return

    existing_columns = {col["name"] for col in inspector.get_columns("analysis_log")}
    alter_statements = []
    if "series_key" not in existing_columns:
        alter_statements.append("ALTER TABLE analysis_log ADD COLUMN series_key VARCHAR(120)")
    if "episode_number" not in existing_columns:
        alter_statements.append("ALTER TABLE analysis_log ADD COLUMN episode_number INTEGER")

    for stmt in alter_statements:
        db.session.execute(text(stmt))
    if alter_statements:
        db.session.commit()
