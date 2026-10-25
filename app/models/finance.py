import enum

from app.extensions import db
from app.models.mixins import TimestampMixin


class ExpenseCategory(str, enum.Enum):
    MATERIAL = "material"
    LABOUR = "labour"
    CONTRACTOR_PAYMENT = "contractor_payment"
    SUPPLIER_PAYMENT = "supplier_payment"
    OTHER = "other"


class ExpenseStatus(str, enum.Enum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    PAID = "paid"
    REJECTED = "rejected"


class Expense(TimestampMixin, db.Model):
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)
    category = db.Column(db.Enum(ExpenseCategory), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    status = db.Column(
        db.Enum(ExpenseStatus), nullable=False, default=ExpenseStatus.PENDING_APPROVAL
    )
    expense_date = db.Column(db.Date, nullable=False)

    recorded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    approved_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    project = db.relationship("Project", back_populates="expenses")
    recorded_by = db.relationship("User", foreign_keys=[recorded_by_id])
    approved_by = db.relationship("User", foreign_keys=[approved_by_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "projectId": self.project_id,
            "category": self.category.value,
            "description": self.description,
            "amount": float(self.amount),
            "status": self.status.value,
            "expenseDate": self.expense_date.isoformat() if self.expense_date else None,
            "recordedBy": self.recorded_by.to_public_dict() if self.recorded_by else None,
            "approvedBy": self.approved_by.to_public_dict() if self.approved_by else None,
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Expense {self.category.value} {self.amount}>"
