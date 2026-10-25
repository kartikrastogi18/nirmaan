import enum
import secrets
import string

from app.extensions import bcrypt, db
from app.models.mixins import TimestampMixin


class UserRole(str, enum.Enum):
    BOSS = "boss"
    PROJECT_MANAGER = "project_manager"
    ARCHITECT = "architect"
    CONTRACTOR = "contractor"
    CLIENT = "client"


class UserStatus(str, enum.Enum):
    PENDING = "pending"  # awaiting Boss approval before first login
    ACTIVE = "active"
    SUSPENDED = "suspended"


_ROLE_PREFIX = {
    UserRole.BOSS: "BOSS",
    UserRole.PROJECT_MANAGER: "PM",
    UserRole.ARCHITECT: "AR",
    UserRole.CONTRACTOR: "TK",  # Thekedar
    UserRole.CLIENT: "CL",
}


def generate_public_id(role: "UserRole") -> str:
    """Human-readable ID shown in the UI, e.g. TW-TK-4821. Never used for auth."""
    suffix = "".join(secrets.choice(string.digits) for _ in range(4))
    return f"TW-{_ROLE_PREFIX[role]}-{suffix}"


class User(TimestampMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True)

    # Only a hash is ever stored. There is deliberately no plaintext/legacy
    # column, so the "half-migrated" bug from the old app can't recur --
    # a User simply cannot exist without a proper hash.
    password_hash = db.Column(db.String(255), nullable=False)

    role = db.Column(db.Enum(UserRole), nullable=False)
    status = db.Column(db.Enum(UserStatus), nullable=False, default=UserStatus.ACTIVE)
    avatar_color = db.Column(db.String(7), default="#15803d")

    # Disambiguated because ProjectAccess has two FKs into users
    # (user_id and granted_by_id).
    project_access = db.relationship(
        "ProjectAccess",
        back_populates="user",
        foreign_keys="ProjectAccess.user_id",
        cascade="all, delete-orphan",
    )
    assigned_tasks = db.relationship(
        "Task", back_populates="assignee", foreign_keys="Task.assignee_id"
    )

    def set_password(self, raw_password: str) -> None:
        if not raw_password or len(raw_password) < 6:
            raise ValueError("Password must be at least 6 characters.")
        self.password_hash = bcrypt.generate_password_hash(raw_password).decode("utf-8")

    def check_password(self, raw_password: str) -> bool:
        if not raw_password or not self.password_hash:
            return False
        return bcrypt.check_password_hash(self.password_hash, raw_password)

    def to_public_dict(self) -> dict:
        """Safe to send to the client -- never includes password_hash."""
        return {
            "id": self.public_id,
            "name": self.name,
            "role": self.role.value,
            "status": self.status.value,
            "avatarColor": self.avatar_color,
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.public_id} {self.role.value}>"
