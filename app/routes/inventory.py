from flask import Blueprint, jsonify, request
import math
from flask_jwt_extended import current_user, jwt_required

from app.extensions import db
from app.models import InventoryItem, MaterialRequest, MovementType, RequestStatus, StockMovement, UserRole
from app.services.access_control import project_access_required, roles_required

inventory_bp = Blueprint("inventory", __name__)

_MANAGER_ROLES = (UserRole.BOSS, UserRole.PROJECT_MANAGER)
_MOVEMENT_DELTA = {"received": 1, "returned": 1, "issued": -1}


def _bad_request(message: str, **extra):
    return jsonify(error=message, **extra), 400


@inventory_bp.get("/<int:project_id>/inventory")
@jwt_required()
@project_access_required
def list_inventory(project_id):
    items = InventoryItem.query.filter_by(project_id=project_id).order_by(InventoryItem.material_name).all()
    return jsonify(items=[i.to_dict() for i in items])


@inventory_bp.post("/<int:project_id>/inventory")
@jwt_required()
@roles_required(*_MANAGER_ROLES)
@project_access_required
def create_inventory_item(project_id):
    data = request.get_json(silent=True)
    if not data:
        return _bad_request("Request body must be JSON.")
    name = (data.get("materialName") or "").strip()
    unit = (data.get("unit") or "").strip()
    if not name:
        return _bad_request("materialName is required.")
    if not unit:
        return _bad_request("unit is required.")

    try:
        current_stock = float(data.get("currentStock") or 0)
        reorder_level = float(data.get("reorderLevel") or 0)
    except (TypeError, ValueError):
        return _bad_request("currentStock and reorderLevel must be numbers.")
    if not math.isfinite(current_stock) or not math.isfinite(reorder_level):
        return _bad_request("Stock values must be finite numbers.")
    if current_stock < 0 or reorder_level < 0:
        return _bad_request("Stock values cannot be negative.")

    item = InventoryItem(
        project_id=project_id,
        material_name=name,
        unit=unit,
        current_stock=current_stock,
        reorder_level=reorder_level,
    )
    db.session.add(item)
    db.session.commit()  # duplicate (project, materialName) -> IntegrityError -> 409
    return jsonify(item=item.to_dict()), 201


@inventory_bp.post("/<int:project_id>/inventory/<int:item_id>/movements")
@jwt_required()
@project_access_required
def record_movement(project_id, item_id):
    """Anyone with project access can record a movement -- this is the
    Contractor's day-to-day 'update material consumption' from the spec,
    not a manager-only action. It's project *membership* that's the gate,
    already enforced by project_access_required above."""
    item = InventoryItem.query.filter_by(id=item_id, project_id=project_id).first()
    if item is None:
        return jsonify(error="No such inventory item."), 404

    data = request.get_json(silent=True)
    if not data:
        return _bad_request("Request body must be JSON.")

    movement_type = data.get("movementType")
    if movement_type not in _MOVEMENT_DELTA:
        return _bad_request(f"movementType must be one of {sorted(_MOVEMENT_DELTA)}.")
    try:
        quantity = float(data.get("quantity"))
    except (TypeError, ValueError):
        return _bad_request("quantity must be a number.")
    if not math.isfinite(quantity) or quantity <= 0:
        return _bad_request("quantity must be a finite number greater than zero.")
    if movement_type == "issued" and quantity > item.current_stock:
        return _bad_request("Cannot issue more material than is currently in stock.")

    item.current_stock += _MOVEMENT_DELTA[movement_type] * quantity
    movement = StockMovement(
        item_id=item.id,
        movement_type=MovementType(movement_type),
        quantity=quantity,
        note=data.get("note"),
        recorded_by=current_user,
    )
    db.session.add(movement)
    db.session.commit()
    return jsonify(item=item.to_dict(), movement=movement.to_dict()), 201


@inventory_bp.get("/<int:project_id>/material-requests")
@jwt_required()
@project_access_required
def list_material_requests(project_id):
    requests_ = (
        MaterialRequest.query.filter_by(project_id=project_id)
        .order_by(MaterialRequest.created_at.desc())
        .all()
    )
    return jsonify(requests=[r.to_dict() for r in requests_])


@inventory_bp.post("/<int:project_id>/material-requests")
@jwt_required()
@project_access_required
def create_material_request(project_id):
    data = request.get_json(silent=True)
    if not data:
        return _bad_request("Request body must be JSON.")
    name = (data.get("materialName") or "").strip()
    if not name:
        return _bad_request("materialName is required.")
    unit = (data.get("unit") or "").strip()
    if not unit:
        return _bad_request("unit is required.")
    try:
        quantity = float(data.get("quantity"))
    except (TypeError, ValueError):
        return _bad_request("quantity must be a number.")
    if not math.isfinite(quantity) or quantity <= 0:
        return _bad_request("quantity must be a finite number greater than zero.")

    req = MaterialRequest(
        project_id=project_id,
        material_name=name,
        quantity=quantity,
        unit=unit,
        requested_by=current_user,
    )
    db.session.add(req)
    db.session.commit()
    return jsonify(request=req.to_dict()), 201


@inventory_bp.patch("/<int:project_id>/material-requests/<int:request_id>")
@jwt_required()
@roles_required(*_MANAGER_ROLES)
@project_access_required
def decide_material_request(project_id, request_id):
    req = MaterialRequest.query.filter_by(id=request_id, project_id=project_id).first()
    if req is None:
        return jsonify(error="No such material request."), 404

    data = request.get_json(silent=True)
    status = data.get("status") if data else None
    valid = {s.value for s in RequestStatus} - {"pending"}
    if status not in valid:
        return _bad_request(f"status must be one of {sorted(valid)}.")

    req.status = RequestStatus(status)
    req.decided_by = current_user
    db.session.commit()
    return jsonify(request=req.to_dict())
