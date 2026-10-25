from app.extensions import db
from app.models.mixins import TimestampMixin


class ProjectFile(TimestampMixin, db.Model):
    __tablename__ = "project_files"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(255), nullable=False, unique=True)
    mime_type = db.Column(db.String(120))
    size_bytes = db.Column(db.Integer, nullable=False, default=0)

    project = db.relationship("Project")
    uploaded_by = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "projectId": self.project_id,
            "name": self.original_name,
            "mimeType": self.mime_type,
            "sizeBytes": self.size_bytes,
            "uploadedBy": self.uploaded_by.to_public_dict() if self.uploaded_by else None,
            "createdAt": self.created_at.isoformat(),
        }
