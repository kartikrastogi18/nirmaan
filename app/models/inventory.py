import enum

from app.extensions import db
from app.models.mixins import TimestampMixin


class RequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FULFILLED = "fulfilled"


class MovementType(str, enum.Enum):
    RECEIVED = "received"
    ISSUED = "issued"
    RETURNED = "returned"


class InventoryItem(TimestampMixin, db.Model):
    __tablename__ = "inventory_items"
    __table_args__ = (
        db.UniqueConstraint("project_id", "material_name", name="uq_project_material"),
    )

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)
    material_name = db.Column(db.String(120), nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    current_stock = db.Column(db.Float, nullable=False, default=0)
    reorder_level = db.Column(db.Float, nullable=False, default=0)

    project = db.relationship("Project", back_populates="inventory_items")
    movements = db.relationship(
        "StockMovement", back_populates="item", cascade="all, delete-orphan"
    )

    @property
    def is_low_stock(self) -> bool:
        return self.current_stock <= self.reorder_level

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "projectId": self.project_id,
            "materialName": self.material_name,
            "unit": self.unit,
            "currentStock": self.current_stock,
            "reorderLevel": self.reorder_level,
            "isLowStock": self.is_low_stock,
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"<InventoryItem {self.material_name} @ project {self.project_id}>"


class StockMovement(TimestampMixin, db.Model):
    """Append-only ledger. current_stock on InventoryItem is a running total
    updated alongside each insert; this table is what makes that total
    auditable instead of just a number someone could silently overwrite."""

    __tablename__ = "stock_movements"

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(
        db.Integer, db.ForeignKey("inventory_items.id"), nullable=False, index=True
    )
    movement_type = db.Column(db.Enum(MovementType), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    note = db.Column(db.String(255))
    recorded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    item = db.relationship("InventoryItem", back_populates="movements")
    recorded_by = db.relationship("User")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "itemId": self.item_id,
            "movementType": self.movement_type.value,
            "quantity": self.quantity,
            "note": self.note,
            "recordedBy": self.recorded_by.to_public_dict() if self.recorded_by else None,
            "createdAt": self.created_at.isoformat(),
        }


class MaterialRequest(TimestampMixin, db.Model):
    __tablename__ = "material_requests"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)
    material_name = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    status = db.Column(db.Enum(RequestStatus), nullable=False, default=RequestStatus.PENDING)

    requested_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    decided_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    project = db.relationship("Project", back_populates="material_requests")
    requested_by = db.relationship("User", foreign_keys=[requested_by_id])
    decided_by = db.relationship("User", foreign_keys=[decided_by_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "projectId": self.project_id,
            "materialName": self.material_name,
            "quantity": self.quantity,
            "unit": self.unit,
            "status": self.status.value,
            "requestedBy": self.requested_by.to_public_dict() if self.requested_by else None,
            "decidedBy": self.decided_by.to_public_dict() if self.decided_by else None,
            "createdAt": self.created_at.isoformat(),
        }
