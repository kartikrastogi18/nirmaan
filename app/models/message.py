from app.extensions import db
from app.models.mixins import TimestampMixin


class Message(TimestampMixin, db.Model):
    """Project-scoped discussion channel. Kept intentionally simple for v1;
    threading/mentions/read-receipts are a natural extension once this core
    schema is validated, not something to guess the shape of up front."""

    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)

    project = db.relationship("Project")
    sender = db.relationship("User")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "projectId": self.project_id,
            "body": self.body,
            "sender": self.sender.to_public_dict() if self.sender else None,
            "createdAt": self.created_at.isoformat(),
        }


class Notification(TimestampMixin, db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=True)
    kind = db.Column(db.String(30), nullable=False)  # "low_stock" | "delay" | "approval" | ...
    text = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)

    recipient = db.relationship("User")
    project = db.relationship("Project")
