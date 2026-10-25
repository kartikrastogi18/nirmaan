"""Initialize database tables, activate pending users, and seed default accounts."""
from app import create_app
from app.extensions import db
from app.models import User, UserRole, UserStatus, Project, ProjectStatus, ProjectAccess, generate_public_id

app = create_app("development")
with app.app_context():
    db.create_all()
    print("Database tables ready.")

    # 1. Activate all pending accounts (boss approval not required)
    pending_users = User.query.filter_by(status=UserStatus.PENDING).all()
    for u in pending_users:
        u.status = UserStatus.ACTIVE
    if pending_users:
        db.session.commit()
        print(f"Auto-activated {len(pending_users)} pending user accounts.")

    # 2. Seed default Boss account if none exists
    boss = User.query.filter((User.phone == "9999999999") | (User.username == "boss")).first()
    if not boss:
        boss = User(
            public_id=generate_public_id(UserRole.BOSS),
            username="boss",
            name="Director / Boss",
            phone="9999999999",
            role=UserRole.BOSS,
            status=UserStatus.ACTIVE,
        )
        boss.set_password("123456")
        db.session.add(boss)
        db.session.commit()
        print("Default Boss account created: boss / 123456")
    else:
        boss.username = "boss"
        boss.status = UserStatus.ACTIVE
        db.session.commit()

    # 3. Seed demo project if empty
    if Project.query.count() == 0:
        proj = Project(
            site_code="GV-01",
            name="Greenview Eco Residency",
            location="Sector 45, Green Park",
            project_type="Residential",
            status=ProjectStatus.ON_TRACK,
            description="Luxury eco-friendly residential villas construction with modern landscaping.",
            budget=15000000,
            spent=4200000,
            progress_percent=38.5,
            planned_progress_percent=40.0,
            created_by_id=boss.id,
        )
        db.session.add(proj)
        db.session.commit()
        print(f"Demo project created: {proj.name} (Site {proj.site_code})")

        # Grant access to kartik accounts
        for u in User.query.filter(User.phone.in_(["0000000000", "1234567891", "1234567899", "1234567890"])).all():
            access = ProjectAccess(user_id=u.id, project_id=proj.id, granted_by_id=boss.id)
            db.session.add(access)
        db.session.commit()
        print("Assigned users to demo project.")

    print("\nReady! Available login accounts:")
    print(" - Boss: username 'boss' / password '123456'")
    print(" - Project Manager: username 'kartik_pm' / password '123456'")
    print(" - Contractor: username 'kartik_contractor' / password '123456'")
    print(" - Architect: username 'kartik_arch' / password '123456'")
    print(" - Client: username 'kartik_client' / password '123456'")

