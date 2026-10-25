import enum

from app.extensions import db
from app.models.mixins import TimestampMixin


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DELAYED = "delayed"
    DONE = "done"


class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Task(TimestampMixin, db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)
    wbs_code = db.Column(db.String(20))
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.Enum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    priority = db.Column(db.Enum(TaskPriority), nullable=False, default=TaskPriority.MEDIUM)
    progress_percent = db.Column(db.Integer, nullable=False, default=0)
    due_date = db.Column(db.Date)
    due_time = db.Column(db.String(5))  # HH:MM local project/user time

    # Two FKs to users -> both relationships below must disambiguate with
    # foreign_keys=, and so must the reverse side (see User.assigned_tasks).
    assignee_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    project = db.relationship("Project", back_populates="tasks")
    assignee = db.relationship(
        "User", back_populates="assigned_tasks", foreign_keys=[assignee_id]
    )
    created_by = db.relationship("User", foreign_keys=[created_by_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "projectId": self.project_id,
            "wbsCode": self.wbs_code,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "progressPercent": self.progress_percent,
            "dueDate": self.due_date.isoformat() if self.due_date else None,
            "dueTime": self.due_time,
            "assignee": self.assignee.to_public_dict() if self.assignee else None,
            "createdBy": self.created_by.to_public_dict() if self.created_by else None,
            "createdAt": self.created_at.isoformat(),
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Task {self.title} [{self.status.value}]>"
