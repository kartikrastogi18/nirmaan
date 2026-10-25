from app.extensions import db
from app.models.mixins import TimestampMixin


class BOQItem(TimestampMixin, db.Model):
    __tablename__ = "boq_items"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)
    description = db.Column(db.String(255), nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    planned_qty = db.Column(db.Float, nullable=False, default=0)
    actual_qty = db.Column(db.Float, nullable=False, default=0)
    rate = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    project = db.relationship("Project", back_populates="boq_items")

    @property
    def qty_variance_pct(self) -> float:
        if not self.planned_qty:
            return 0.0
        return round(((self.actual_qty - self.planned_qty) / self.planned_qty) * 100, 1)

    @property
    def cost_variance(self) -> float:
        return float(self.rate) * (self.actual_qty - self.planned_qty)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<BOQItem {self.description[:30]!r}>"
