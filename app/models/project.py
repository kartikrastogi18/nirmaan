import enum

from app.extensions import db
from app.models.mixins import TimestampMixin


class ProjectStatus(str, enum.Enum):
    ON_TRACK = "on_track"
    DELAYED = "delayed"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"


class Project(TimestampMixin, db.Model):
    """A construction site.

    This is the isolation boundary described in the spec's "Site-Based Access
    Architecture": nearly every other table below carries a project_id, and
    who may read/write a given project_id is decided in exactly one place --
    app/services/access_control.py -- not re-implemented per route.
    """

    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    site_code = db.Column(db.String(10), unique=True, nullable=False)  # "A", "B" -- shown in UI
    name = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(200))
    project_type = db.Column(db.String(50))  # Residential / Commercial / Infrastructure
    status = db.Column(db.Enum(ProjectStatus), nullable=False, default=ProjectStatus.ON_TRACK)
    description = db.Column(db.Text)

    # Numeric, not Float: SQLAlchemy emulates fixed-point Numeric on SQLite via
    # Decimal<->str conversion, so money is never subject to binary-float
    # rounding the way a Float column would be.
    budget = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    spent = db.Column(db.Numeric(14, 2), nullable=False, default=0)

    progress_percent = db.Column(db.Float, nullable=False, default=0)
    planned_progress_percent = db.Column(db.Float, nullable=False, default=0)

    start_date = db.Column(db.Date)
    target_end_date = db.Column(db.Date)
    actual_end_date = db.Column(db.Date)

    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_by = db.relationship("User", foreign_keys=[created_by_id])

    access_grants = db.relationship(
        "ProjectAccess", back_populates="project", cascade="all, delete-orphan"
    )
    tasks = db.relationship("Task", back_populates="project", cascade="all, delete-orphan")
    inventory_items = db.relationship(
        "InventoryItem", back_populates="project", cascade="all, delete-orphan"
    )
    material_requests = db.relationship(
        "MaterialRequest", back_populates="project", cascade="all, delete-orphan"
    )
    drawings = db.relationship("Drawing", back_populates="project", cascade="all, delete-orphan")
    boq_items = db.relationship("BOQItem", back_populates="project", cascade="all, delete-orphan")
    expenses = db.relationship("Expense", back_populates="project", cascade="all, delete-orphan")
    labour_records = db.relationship(
        "LabourRecord", back_populates="project", cascade="all, delete-orphan"
    )
    progress_logs = db.relationship(
        "ProgressLog", back_populates="project", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "siteCode": self.site_code,
            "name": self.name,
            "location": self.location,
            "projectType": self.project_type,
            "status": self.status.value,
            "description": self.description,
            "budget": float(self.budget),
            "spent": float(self.spent),
            "progressPercent": self.progress_percent,
            "plannedProgressPercent": self.planned_progress_percent,
            "startDate": self.start_date.isoformat() if self.start_date else None,
            "targetEndDate": self.target_end_date.isoformat() if self.target_end_date else None,
            "actualEndDate": self.actual_end_date.isoformat() if self.actual_end_date else None,
            "createdBy": self.created_by.to_public_dict() if self.created_by else None,
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Project {self.site_code} {self.name}>"
