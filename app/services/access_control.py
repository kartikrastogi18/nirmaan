"""
Central home for the two rules the spec calls out explicitly:

  1. RBAC       -- a user's `role` determines what actions/UI they're allowed.
  2. Site isolation -- a user only ever sees the specific projects they hold
                       a ProjectAccess grant for. Boss is the sole exception
                       and sees every project unconditionally.

Nothing outside this module should query ProjectAccess directly. Every route
that touches a project-scoped resource calls into here, so the isolation
rule can't quietly drift or get forgotten in one particular endpoint --
which is exactly the failure mode a per-route reimplementation invites.

Revision note: the project-skeleton drop used a placeholder `g.current_user`
here since no auth layer existed yet. Now that JWT auth is wired up
(app/__init__.py registers a user_lookup_loader), this uses Flask-JWT-
Extended's own `current_user` proxy instead -- one fewer thing for a route
to remember to set up by hand.
"""
from functools import wraps

from flask import jsonify
from flask_jwt_extended import current_user

from app.models.access import ProjectAccess
from app.models.project import Project
from app.models.user import UserRole


def require_project_access(user, project_id: int) -> bool:
    """True if `user` may view/act on `project_id`."""
    if user.role == UserRole.BOSS:
        return True
    return (
        ProjectAccess.query.filter_by(user_id=user.id, project_id=project_id).first()
        is not None
    )


def visible_project_ids(user) -> list:
    """Every project id `user` is allowed to see, Boss included."""
    if user.role == UserRole.BOSS:
        return [row.id for row in Project.query.with_entities(Project.id).all()]
    grants = ProjectAccess.query.filter_by(user_id=user.id).all()
    return [grant.project_id for grant in grants]


def visible_projects_query(user):
    """Same rule as visible_project_ids, as a Query -- lets a route add its
    own filtering/pagination/ordering without loading every row into memory
    first."""
    if user.role == UserRole.BOSS:
        return Project.query
    return Project.query.join(ProjectAccess).filter(ProjectAccess.user_id == user.id)


def project_access_required(view_fn):
    """Route decorator enforcing site isolation. Must sit *inside*
    @jwt_required() (i.e. written below it) so `current_user` is already
    populated. Returns 403 with no detail about *why* -- a user with no
    grant shouldn't be able to distinguish 'exists but not yours' from
    'does not exist'."""

    @wraps(view_fn)
    def wrapper(*args, project_id=None, **kwargs):
        if project_id is None or not require_project_access(current_user, int(project_id)):
            return jsonify(error="You don't have access to this project."), 403
        return view_fn(*args, project_id=project_id, **kwargs)

    return wrapper


def roles_required(*allowed_roles: UserRole):
    """Route decorator restricting an endpoint to specific roles, independent
    of which project is involved -- e.g. only Boss can approve new accounts,
    only Architect can upload a drawing revision. Also must sit inside
    @jwt_required()."""

    def decorator(view_fn):
        @wraps(view_fn)
        def wrapper(*args, **kwargs):
            if current_user is None or current_user.role not in allowed_roles:
                return jsonify(error="You don't have permission to do that."), 403
            return view_fn(*args, **kwargs)

        return wrapper

    return decorator
