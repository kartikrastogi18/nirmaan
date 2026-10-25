from app.extensions import db
from app.models.mixins import TimestampMixin


class AuditLog(TimestampMixin, db.Model):
    """Append-only trail for the spec's 'Audit logs / Activity tracking'
    requirement under Security & Access Control. Rows are only ever
    inserted, never updated or deleted, by convention -- there's no
    updated_at-driven business logic that would ever touch an existing row."""

    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=True)
    action = db.Column(db.String(50), nullable=False)  # "login" | "drawing.approve" | ...
    entity_type = db.Column(db.String(50))
    entity_id = db.Column(db.Integer)
    detail = db.Column(db.Text)
    ip_address = db.Column(db.String(45))

    actor = db.relationship("User")
    project = db.relationship("Project")
