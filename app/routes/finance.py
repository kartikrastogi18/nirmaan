from datetime import date
import math

from flask import Blueprint, jsonify, request
from flask_jwt_extended import current_user, jwt_required

from app.extensions import db
from app.models import Expense, ExpenseCategory, ExpenseStatus, UserRole
from app.services.access_control import project_access_required, roles_required

finance_bp = Blueprint("finance", __name__)

_MANAGER_ROLES = (UserRole.BOSS, UserRole.PROJECT_MANAGER)


def _bad_request(message: str, **extra):
    return jsonify(error=message, **extra), 400


def _parse_date(value, field_name: str):
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an ISO date (YYYY-MM-DD).") from exc


@finance_bp.get("/<int:project_id>/expenses")
@jwt_required()
@project_access_required
def list_expenses(project_id):
    expenses = (
        Expense.query.filter_by(project_id=project_id).order_by(Expense.expense_date.desc()).all()
    )
    by_category = {}
    for e in expenses:
        by_category[e.category.value] = by_category.get(e.category.value, 0) + float(e.amount)
    return jsonify(
        expenses=[e.to_dict() for e in expenses],
        totalByCategory=by_category,
    )


@finance_bp.post("/<int:project_id>/expenses")
@jwt_required()
@project_access_required
def create_expense(project_id):
    """Anyone with project access can submit an expense for approval -- the
    spec's 'Expense approvals' implies a submit-then-approve flow, not that
    only a manager ever records one (a Contractor logging a supplier
    payment they made on-site is the common case)."""
    data = request.get_json(silent=True)
    if not data:
        return _bad_request("Request body must be JSON.")

    category = data.get("category")
    valid_categories = {c.value for c in ExpenseCategory}
    if category not in valid_categories:
        return _bad_request(f"category must be one of {sorted(valid_categories)}.")
    description = (data.get("description") or "").strip()
    if not description:
        return _bad_request("description is required.")
    try:
        amount = float(data.get("amount"))
    except (TypeError, ValueError):
        return _bad_request("amount must be a number.")
    if not math.isfinite(amount) or amount <= 0:
        return _bad_request("amount must be a finite number greater than zero.")

    try:
        expense_date = _parse_date(data.get("expenseDate"), "expenseDate") or date.today()
    except ValueError as exc:
        return _bad_request(str(exc))

    expense = Expense(
        project_id=project_id,
        category=ExpenseCategory(category),
        description=description,
        amount=amount,
        expense_date=expense_date,
        recorded_by=current_user,
    )
    db.session.add(expense)
    db.session.commit()
    return jsonify(expense=expense.to_dict()), 201


@finance_bp.patch("/<int:project_id>/expenses/<int:expense_id>")
@jwt_required()
@roles_required(*_MANAGER_ROLES)
@project_access_required
def decide_expense(project_id, expense_id):
    """Only PAID actually moves money against the project's budget --
    approving is a checkpoint, paying is when it counts as spent. The
    delta is only ever applied on the transition *into* paid, so toggling
    status back and forth can't double- or under-count it."""
    expense = Expense.query.filter_by(id=expense_id, project_id=project_id).first()
    if expense is None:
        return jsonify(error="No such expense."), 404

    data = request.get_json(silent=True)
    status = data.get("status") if data else None
    valid = {s.value for s in ExpenseStatus} - {"pending_approval"}
    if status not in valid:
        return _bad_request(f"status must be one of {sorted(valid)}.")

    was_paid = expense.status == ExpenseStatus.PAID
    expense.status = ExpenseStatus(status)
    expense.approved_by = current_user
    if expense.status == ExpenseStatus.PAID and not was_paid:
        expense.project.spent = float(expense.project.spent) + float(expense.amount)
    elif was_paid and expense.status != ExpenseStatus.PAID:
        expense.project.spent = float(expense.project.spent) - float(expense.amount)

    db.session.commit()
    return jsonify(expense=expense.to_dict(), projectSpent=float(expense.project.spent))
