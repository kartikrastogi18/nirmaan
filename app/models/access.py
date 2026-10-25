from app.extensions import db
from app.models.mixins import TimestampMixin


class ProjectAccess(TimestampMixin, db.Model):
    """Grants one user access to one project/site.

    This row's existence *is* the site-isolation rule: a Project Manager,
    Architect, Contractor, or Client can see a project if and only if a row
    exists here for (their user_id, that project_id). Boss is the one
    exception and bypasses this table entirely -- see
    app/services/access_control.py, which is the single place that rule is
    implemented so it can't drift between routes.
    """

    __tablename__ = "project_access"
    __table_args__ = (
        db.UniqueConstraint("user_id", "project_id", name="uq_user_project"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)
    granted_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    user = db.relationship(
        "User", back_populates="project_access", foreign_keys=[user_id]
    )
    project = db.relationship("Project", back_populates="access_grants")
    granted_by = db.relationship("User", foreign_keys=[granted_by_id])

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ProjectAccess user={self.user_id} project={self.project_id}>"
