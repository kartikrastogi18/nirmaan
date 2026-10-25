from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.services import calculators as calc

calculators_bp = Blueprint("calculators", __name__)


def _bad_request(message: str, **extra):
    return jsonify(error=message, **extra), 400


def _num(data, key, required=True, default=None):
    if key not in data or data[key] in (None, ""):
        if required:
            raise ValueError(f"{key} is required.")
        return default
    try:
        return float(data[key])
    except (TypeError, ValueError):
        raise ValueError(f"{key} must be a number.")


@calculators_bp.post("/concrete")
@jwt_required()
def concrete():
    data = request.get_json(silent=True) or {}
    try:
        result = calc.concrete_quantities(
            _num(data, "lengthM"),
            _num(data, "widthM"),
            _num(data, "thicknessM"),
            data.get("mix", "M20"),
        )
    except ValueError as exc:
        return _bad_request(str(exc))
    return jsonify(result=result)


@calculators_bp.post("/steel")
@jwt_required()
def steel():
    data = request.get_json(silent=True) or {}
    try:
        result = calc.steel_weight(
            _num(data, "diameterMm"), _num(data, "lengthM"), int(_num(data, "quantity"))
        )
    except ValueError as exc:
        return _bad_request(str(exc))
    return jsonify(result=result)


@calculators_bp.post("/brick")
@jwt_required()
def brick():
    data = request.get_json(silent=True) or {}
    try:
        result = calc.brick_quantities(
            _num(data, "wallLengthM"),
            _num(data, "wallHeightM"),
            _num(data, "wallThicknessM"),
            data.get("brickSize", "modular"),
            _num(data, "mortarThicknessMm", required=False, default=10),
        )
    except ValueError as exc:
        return _bad_request(str(exc))
    return jsonify(result=result)


@calculators_bp.post("/plaster")
@jwt_required()
def plaster():
    data = request.get_json(silent=True) or {}
    try:
        result = calc.plaster_quantities(
            _num(data, "areaM2"), _num(data, "thicknessM"), data.get("mix", "1:6")
        )
    except ValueError as exc:
        return _bad_request(str(exc))
    return jsonify(result=result)


@calculators_bp.post("/excavation")
@jwt_required()
def excavation():
    data = request.get_json(silent=True) or {}
    try:
        result = calc.excavation_quantities(
            _num(data, "lengthM"),
            _num(data, "widthM"),
            _num(data, "depthM"),
            _num(data, "bulkingPct", required=False, default=25),
        )
    except ValueError as exc:
        return _bad_request(str(exc))
    return jsonify(result=result)


@calculators_bp.post("/structural")
@jwt_required()
def structural():
    data = request.get_json(silent=True) or {}
    try:
        result = calc.structural_quantities(
            data.get("element", ""),
            _num(data, "lengthM"),
            _num(data, "widthM"),
            _num(data, "heightM"),
            int(_num(data, "count")),
        )
    except ValueError as exc:
        return _bad_request(str(exc))
    return jsonify(result=result)
