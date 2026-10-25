import enum

from app.extensions import db
from app.models.mixins import TimestampMixin


class DrawingCategory(str, enum.Enum):
    ARCHITECTURAL = "architectural"
    STRUCTURAL = "structural"
    ELECTRICAL = "electrical"
    PLUMBING = "plumbing"
    BOQ = "boq"


class RevisionStatus(str, enum.Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved_for_construction"
    REVISION_REQUIRED = "revision_required"
    REJECTED = "rejected"


class Drawing(TimestampMixin, db.Model):
    """A drawing's identity (name/category) is stable; each upload is a
    DrawingRevision underneath it, which is what gives real version history
    instead of a file that gets silently overwritten."""

    __tablename__ = "drawings"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.Enum(DrawingCategory), nullable=False)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    project = db.relationship("Project", back_populates="drawings")
    uploaded_by = db.relationship("User")
    revisions = db.relationship(
        "DrawingRevision",
        back_populates="drawing",
        cascade="all, delete-orphan",
        order_by="DrawingRevision.created_at.desc()",
    )

    @property
    def latest_revision(self):
        return self.revisions[0] if self.revisions else None

    def to_dict(self) -> dict:
        latest = self.latest_revision
        return {
            "id": self.id,
            "projectId": self.project_id,
            "name": self.name,
            "category": self.category.value,
            "uploadedBy": self.uploaded_by.to_public_dict() if self.uploaded_by else None,
            "latestRevision": latest.to_dict() if latest else None,
            "revisionCount": len(self.revisions),
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Drawing {self.name} ({self.category.value})>"


class DrawingRevision(TimestampMixin, db.Model):
    __tablename__ = "drawing_revisions"

    id = db.Column(db.Integer, primary_key=True)
    drawing_id = db.Column(db.Integer, db.ForeignKey("drawings.id"), nullable=False, index=True)
    version_label = db.Column(db.String(20), nullable=False)  # "Rev 1", "Rev 2"...
    file_path = db.Column(db.String(500), nullable=False)
    status = db.Column(
        db.Enum(RevisionStatus), nullable=False, default=RevisionStatus.PENDING_REVIEW
    )
    review_notes = db.Column(db.Text)

    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    drawing = db.relationship("Drawing", back_populates="revisions")
    uploaded_by = db.relationship("User", foreign_keys=[uploaded_by_id])
    reviewed_by = db.relationship("User", foreign_keys=[reviewed_by_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "drawingId": self.drawing_id,
            "versionLabel": self.version_label,
            "filePath": self.file_path,
            "status": self.status.value,
            "reviewNotes": self.review_notes,
            "uploadedBy": self.uploaded_by.to_public_dict() if self.uploaded_by else None,
            "reviewedBy": self.reviewed_by.to_public_dict() if self.reviewed_by else None,
            "createdAt": self.created_at.isoformat(),
        }
