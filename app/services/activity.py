from app.extensions import db
from app.models import AuditLog, Notification, ProjectAccess, User, UserRole, UserStatus


def record(actor, project_id, action, detail, entity_type=None, entity_id=None):
    db.session.add(AuditLog(actor_id=actor.id if actor else None, project_id=project_id, action=action,
                            entity_type=entity_type, entity_id=entity_id, detail=detail))


def notify_project(project_id, text, kind="update", exclude_user_id=None, only_user_id=None):
    if only_user_id:
        ids = [only_user_id]
    else:
        ids = [a.user_id for a in ProjectAccess.query.filter_by(project_id=project_id).all()]
        # Boss/Admin has implicit access to every project and therefore has no
        # ProjectAccess row. Include active bosses so the owner still receives
        # project notifications in the Personal Edition.
        ids.extend(u.id for u in User.query.filter_by(role=UserRole.BOSS, status=UserStatus.ACTIVE).all())
    for uid in set(ids):
        if uid == exclude_user_id:
            continue
        db.session.add(Notification(recipient_id=uid, project_id=project_id, kind=kind, text=text))
