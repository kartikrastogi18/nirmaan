import enum

from app.extensions import db
from app.models.mixins import TimestampMixin


class Trade(str, enum.Enum):
    MASON = "mason"
    BAR_BENDER = "bar_bender"
    CARPENTER = "carpenter"
    HELPER = "helper"
    ELECTRICIAN = "electrician"
    PLUMBER = "plumber"


class LabourRecord(TimestampMixin, db.Model):
    """One row per (project, date, trade). The unique constraint means the
    field UI is a simple upsert: tapping + / - on 'Masons' for today just
    updates this one row's headcount, which is exactly the tap-friendly
    stepper interaction the mobile UI needs -- no separate 'create a new
    attendance entry' flow required."""

    __tablename__ = "labour_records"
    __table_args__ = (
        db.UniqueConstraint("project_id", "record_date", "trade", name="uq_labour_day_trade"),
    )

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)
    record_date = db.Column(db.Date, nullable=False)
    trade = db.Column(db.Enum(Trade), nullable=False)
    headcount = db.Column(db.Integer, nullable=False, default=0)
    recorded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    project = db.relationship("Project", back_populates="labour_records")
    recorded_by = db.relationship("User")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "projectId": self.project_id,
            "recordDate": self.record_date.isoformat(),
            "trade": self.trade.value,
            "headcount": self.headcount,
            "recordedBy": self.recorded_by.to_public_dict() if self.recorded_by else None,
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"<LabourRecord {self.trade.value} x{self.headcount} @ {self.record_date}>"
