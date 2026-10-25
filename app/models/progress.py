from app.extensions import db
from app.models.mixins import TimestampMixin


class ProgressLog(TimestampMixin, db.Model):
    """A Daily Work Report -- the Contractor's site diary entry that photos,
    voice notes, and the progress timeline all attach to."""

    __tablename__ = "progress_logs"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    log_date = db.Column(db.Date, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    progress_percent_snapshot = db.Column(db.Float)

    audio_note_path = db.Column(db.String(500))
    audio_transcript = db.Column(db.Text)  # filled in async by the voice-to-text job

    project = db.relationship("Project", back_populates="progress_logs")
    author = db.relationship("User")
    photos = db.relationship(
        "ProgressPhoto", back_populates="log", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ProgressLog {self.title!r} @ {self.log_date}>"


class ProgressPhoto(TimestampMixin, db.Model):
    __tablename__ = "progress_photos"

    id = db.Column(db.Integer, primary_key=True)
    log_id = db.Column(
        db.Integer, db.ForeignKey("progress_logs.id"), nullable=False, index=True
    )
    file_path = db.Column(db.String(500), nullable=False)
    caption = db.Column(db.String(255))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    accuracy_m = db.Column(db.Float)
    captured_at = db.Column(db.DateTime)

    log = db.relationship("ProgressLog", back_populates="photos")
