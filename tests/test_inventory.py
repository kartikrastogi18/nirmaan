from app.models import InventoryItem, MaterialRequest, Project, ProjectAccess, UserRole


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def _make_project(db, boss, code="A", name="Skyline Residency"):
    project = Project(site_code=code, name=name, created_by=boss)
    db.session.add(project)
    db.session.commit()
    return project


def _grant(db, user, project, boss):
    db.session.add(ProjectAccess(user_id=user.id, project_id=project.id, granted_by_id=boss.id))
    db.session.commit()


class TestInventoryItems:
    def test_manager_can_create_an_item(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9300000001")
        site = _make_project(db, boss, "A")
        resp = client.post(
            f"/api/projects/{site.id}/inventory",
            json={"materialName": "OPC Cement", "unit": "bags", "currentStock": 120, "reorderLevel": 200},
            headers=_auth_header(token_for(boss)),
        )
        assert resp.status_code == 201
        assert resp.get_json()["item"]["isLowStock"] is True

    def test_contractor_cannot_create_an_item(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9300000002")
        contractor = make_user(UserRole.CONTRACTOR, "9300000003")
        site = _make_project(db, boss, "A")
        _grant(db, contractor, site, boss)
        resp = client.post(
            f"/api/projects/{site.id}/inventory",
            json={"materialName": "OPC Cement", "unit": "bags"},
            headers=_auth_header(token_for(contractor)),
        )
        assert resp.status_code == 403

    def test_duplicate_material_name_on_same_project_is_rejected(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9300000004")
        site = _make_project(db, boss, "A")
        token = token_for(boss)
        client.post(
            f"/api/projects/{site.id}/inventory",
            json={"materialName": "Cement", "unit": "bags"},
            headers=_auth_header(token),
        )
        resp = client.post(
            f"/api/projects/{site.id}/inventory",
            json={"materialName": "Cement", "unit": "bags"},
            headers=_auth_header(token),
        )
        assert resp.status_code == 409


class TestStockMovements:
    def test_contractor_can_record_consumption(self, client, db, make_user, token_for):
        # This is a field-data-entry action, gated by project access, not role.
        boss = make_user(UserRole.BOSS, "9300000010")
        contractor = make_user(UserRole.CONTRACTOR, "9300000011")
        site = _make_project(db, boss, "A")
        _grant(db, contractor, site, boss)
        item = InventoryItem(project_id=site.id, material_name="Cement", unit="bags", current_stock=100)
        db.session.add(item)
        db.session.commit()

        resp = client.post(
            f"/api/projects/{site.id}/inventory/{item.id}/movements",
            json={"movementType": "issued", "quantity": 40},
            headers=_auth_header(token_for(contractor)),
        )
        assert resp.status_code == 201
        assert resp.get_json()["item"]["currentStock"] == 60

    def test_received_increases_stock_returned_also_increases(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9300000012")
        site = _make_project(db, boss, "A")
        item = InventoryItem(project_id=site.id, material_name="Steel", unit="tonnes", current_stock=2)
        db.session.add(item)
        db.session.commit()
        token = token_for(boss)

        client.post(
            f"/api/projects/{site.id}/inventory/{item.id}/movements",
            json={"movementType": "received", "quantity": 3},
            headers=_auth_header(token),
        )
        resp = client.post(
            f"/api/projects/{site.id}/inventory/{item.id}/movements",
            json={"movementType": "returned", "quantity": 0.5},
            headers=_auth_header(token),
        )
        assert resp.get_json()["item"]["currentStock"] == 5.5

    def test_negative_quantity_is_rejected(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9300000013")
        site = _make_project(db, boss, "A")
        item = InventoryItem(project_id=site.id, material_name="Sand", unit="truckloads", current_stock=10)
        db.session.add(item)
        db.session.commit()

        resp = client.post(
            f"/api/projects/{site.id}/inventory/{item.id}/movements",
            json={"movementType": "issued", "quantity": -5},
            headers=_auth_header(token_for(boss)),
        )
        assert resp.status_code == 400


class TestMaterialRequests:
    def test_contractor_can_request_material(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9300000020")
        contractor = make_user(UserRole.CONTRACTOR, "9300000021")
        site = _make_project(db, boss, "A")
        _grant(db, contractor, site, boss)

        resp = client.post(
            f"/api/projects/{site.id}/material-requests",
            json={"materialName": "TMT Steel", "quantity": 2, "unit": "tonnes"},
            headers=_auth_header(token_for(contractor)),
        )
        assert resp.status_code == 201
        assert resp.get_json()["request"]["status"] == "pending"

    def test_only_manager_can_approve(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9300000022")
        contractor = make_user(UserRole.CONTRACTOR, "9300000023")
        site = _make_project(db, boss, "A")
        _grant(db, contractor, site, boss)
        req = MaterialRequest(
            project_id=site.id, material_name="Bricks", quantity=5000, unit="nos", requested_by=contractor
        )
        db.session.add(req)
        db.session.commit()

        denied = client.patch(
            f"/api/projects/{site.id}/material-requests/{req.id}",
            json={"status": "approved"},
            headers=_auth_header(token_for(contractor)),
        )
        assert denied.status_code == 403

        approved = client.patch(
            f"/api/projects/{site.id}/material-requests/{req.id}",
            json={"status": "approved"},
            headers=_auth_header(token_for(boss)),
        )
        assert approved.status_code == 200
        assert approved.get_json()["request"]["status"] == "approved"
