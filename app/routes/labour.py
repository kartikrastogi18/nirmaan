from datetime import date

from flask import Blueprint, jsonify, request
from flask_jwt_extended import current_user, jwt_required

from app.extensions import db
from app.models import LabourRecord, Trade
from app.services.access_control import project_access_required

labour_bp = Blueprint("labour", __name__)


def _bad_request(message: str, **extra):
    return jsonify(error=message, **extra), 400


def _parse_date(value, field_name: str):
    if value in (None, ""):
        return date.today()
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an ISO date (YYYY-MM-DD).") from exc


@labour_bp.get("/<int:project_id>/labour")
@jwt_required()
@project_access_required
def get_labour(project_id):
    try:
        for_date = _parse_date(request.args.get("date"), "date")
    except ValueError as exc:
        return _bad_request(str(exc))

    records = LabourRecord.query.filter_by(project_id=project_id, record_date=for_date).all()
    by_trade = {r.trade.value: r.to_dict() for r in records}
    # Every trade appears even with zero headcount, so the stepper UI has a
    # fixed set of rows to render rather than needing to invent a row the
    # first time someone taps "+" on a trade with no record yet today.
    for trade in Trade:
        by_trade.setdefault(
            trade.value,
            {
                "id": None,
                "projectId": project_id,
                "recordDate": for_date.isoformat(),
                "trade": trade.value,
                "headcount": 0,
                "recordedBy": None,
            },
        )
    return jsonify(date=for_date.isoformat(), trades=by_trade)


@labour_bp.put("/<int:project_id>/labour")
@jwt_required()
@project_access_required
def set_labour(project_id):
    """Upsert one trade's headcount for one day. This is deliberately the
    entire API surface a stepper button needs: it sends the new absolute
    count on every tap, this either creates or updates the one row for
    (project, date, trade) -- the unique constraint on LabourRecord is what
    makes 'upsert' well-defined instead of ambiguous."""
    data = request.get_json(silent=True)
    if not data:
        return _bad_request("Request body must be JSON.")

    trade = data.get("trade")
    valid_trades = {t.value for t in Trade}
    if trade not in valid_trades:
        return _bad_request(f"trade must be one of {sorted(valid_trades)}.")

    headcount = data.get("headcount")
    if not isinstance(headcount, int) or isinstance(headcount, bool) or headcount < 0:
        return _bad_request("headcount must be a non-negative integer.")

    try:
        record_date = _parse_date(data.get("date"), "date")
    except ValueError as exc:
        return _bad_request(str(exc))

    record = LabourRecord.query.filter_by(
        project_id=project_id, record_date=record_date, trade=Trade(trade)
    ).first()
    if record is None:
        record = LabourRecord(
            project_id=project_id, record_date=record_date, trade=Trade(trade), headcount=headcount
        )
        db.session.add(record)
    else:
        record.headcount = headcount
    record.recorded_by = current_user

    db.session.commit()
    return jsonify(record=record.to_dict())
