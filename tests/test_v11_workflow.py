from io import BytesIO
from app.extensions import db
from app.models import Project, ProjectAccess, UserRole


def h(token): return {"Authorization": f"Bearer {token}"}

def setup_project(make_user, token_for):
    boss=make_user(UserRole.BOSS,"9111111111","Boss")
    pm=make_user(UserRole.PROJECT_MANAGER,"9222222222","PM")
    client_user=make_user(UserRole.CLIENT,"9333333333","Client")
    project=Project(site_code="V11",name="V1.1 Site",created_by_id=boss.id)
    db.session.add(project); db.session.flush()
    db.session.add_all([ProjectAccess(user_id=pm.id,project_id=project.id,granted_by_id=boss.id),ProjectAccess(user_id=client_user.id,project_id=project.id,granted_by_id=boss.id)])
    db.session.commit()
    return boss,pm,client_user,project,token_for(boss),token_for(pm),token_for(client_user)

def test_pm_cannot_edit_financials(client, make_user, token_for):
    _,_,_,p,_,pm_t,_=setup_project(make_user,token_for)
    assert client.patch(f"/api/projects/{p.id}",json={"budget":999},headers=h(pm_t)).status_code==403

def test_manual_overall_progress_rejected(client, make_user, token_for):
    *_,p,boss_t,_,_=setup_project(make_user,token_for)
    assert client.patch(f"/api/projects/{p.id}",json={"progressPercent":88},headers=h(boss_t)).status_code==400

def test_client_can_post_geotagged_photo(client, make_user, token_for):
    *_,p,_,_,client_t=setup_project(make_user,token_for)
    data={"title":"Client photo","latitude":"28.6139","longitude":"77.2090","accuracyM":"12","photos":(BytesIO(b"\xff\xd8\xff\xe0"+b"x"*64),"site.jpg")}
    r=client.post(f"/api/projects/{p.id}/progress",data=data,headers=h(client_t),content_type="multipart/form-data")
    assert r.status_code==201
    photo=r.get_json()["update"]["photos"][0]
    assert photo["latitude"]==28.6139 and photo["longitude"]==77.2090

def test_task_progress_recalculates_project(client, make_user, token_for):
    *_,p,boss_t,_,_=setup_project(make_user,token_for)
    a=client.post(f"/api/projects/{p.id}/tasks",json={"title":"A"},headers=h(boss_t)).get_json()["task"]["id"]
    b=client.post(f"/api/projects/{p.id}/tasks",json={"title":"B"},headers=h(boss_t)).get_json()["task"]["id"]
    client.patch(f"/api/projects/{p.id}/tasks/{a}",json={"progressPercent":100},headers=h(boss_t))
    client.patch(f"/api/projects/{p.id}/tasks/{b}",json={"progressPercent":50},headers=h(boss_t))
    got=client.get(f"/api/projects/{p.id}",headers=h(boss_t)).get_json()["project"]
    assert got["progressPercent"]==75.0

def test_task_deadline_time_round_trip(client, make_user, token_for):
    *_,p,boss_t,_,_=setup_project(make_user,token_for)
    r=client.post(f"/api/projects/{p.id}/tasks",json={"title":"Timed","dueDate":"2026-10-26","dueTime":"17:30"},headers=h(boss_t))
    assert r.status_code==201 and r.get_json()["task"]["dueTime"]=="17:30"
