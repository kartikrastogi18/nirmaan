import pytest

from app.models import UserRole
from app.services import calculators as calc


class TestConcreteCalculator:
    def test_known_values_m20_mix(self):
        # 5m x 4m x 0.15m slab, M20 (1:1.5:3) -- hand-verified:
        # wet=3.0, dry=4.62, cement=0.84 m3 -> 1209.6kg -> 25 bags (ceil)
        result = calc.concrete_quantities(5, 4, 0.15, "M20")
        assert result["wetVolumeM3"] == pytest.approx(3.0)
        assert result["dryVolumeM3"] == pytest.approx(4.62)
        assert result["cementBags"] == 25
        assert result["sandVolumeM3"] == pytest.approx(1.26)
        assert result["aggregateVolumeM3"] == pytest.approx(2.52)

    def test_unknown_mix_raises(self):
        with pytest.raises(ValueError):
            calc.concrete_quantities(5, 4, 0.15, "M99")


class TestSteelCalculator:
    def test_known_values(self):
        # 12mm bar, 12m long, 50 bars: unit weight = 144/162.28
        result = calc.steel_weight(12, 12, 50)
        expected_unit = (12 ** 2) / 162.28
        assert result["unitWeightKgPerM"] == pytest.approx(expected_unit, rel=1e-3)
        assert result["totalWeightKg"] == pytest.approx(expected_unit * 12 * 50, rel=1e-3)


class TestBrickCalculator:
    def test_modular_brick_wall(self):
        result = calc.brick_quantities(10, 3, 0.23, "modular", 10)
        # Wall volume must be exact regardless of brick math
        assert result["wallVolumeM3"] == pytest.approx(6.9)
        assert result["bricksRequired"] > 0
        assert result["cementBags"] > 0

    def test_unknown_brick_size_raises(self):
        with pytest.raises(ValueError):
            calc.brick_quantities(10, 3, 0.23, "giant", 10)


class TestPlasterCalculator:
    def test_known_values(self):
        result = calc.plaster_quantities(100, 0.012, "1:6")
        assert result["wetVolumeM3"] == pytest.approx(1.2)
        assert result["dryVolumeM3"] == pytest.approx(1.596)

    def test_invalid_mix_raises(self):
        with pytest.raises(ValueError):
            calc.plaster_quantities(100, 0.012, "1:99")


class TestExcavationCalculator:
    def test_known_values(self):
        result = calc.excavation_quantities(12, 8, 1.5, 25)
        assert result["bankVolumeM3"] == pytest.approx(144.0)
        assert result["bulkedVolumeM3"] == pytest.approx(180.0)
        assert result["tipperTruckLoads"] == 30


class TestStructuralCalculator:
    def test_column_reinforcement_ratio(self):
        result = calc.structural_quantities("column", 0.4, 0.4, 3, 12)
        assert result["singleVolumeM3"] == pytest.approx(0.48)
        assert result["totalVolumeM3"] == pytest.approx(5.76)
        assert result["reinforcementRatioPct"] == pytest.approx(2.0)

    def test_unknown_element_raises(self):
        with pytest.raises(ValueError):
            calc.structural_quantities("staircase", 1, 1, 1, 1)


class TestCalculatorRoutes:
    def test_requires_authentication(self, client):
        resp = client.post("/api/calculators/concrete", json={"lengthM": 5, "widthM": 4, "thicknessM": 0.15})
        assert resp.status_code == 401

    def test_concrete_route_matches_service_function(self, client, db, make_user, token_for):
        user = make_user(UserRole.CONTRACTOR, "9200000001")
        resp = client.post(
            "/api/calculators/concrete",
            json={"lengthM": 5, "widthM": 4, "thicknessM": 0.15, "mix": "M20"},
            headers={"Authorization": f"Bearer {token_for(user)}"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["result"]["cementBags"] == 25

    def test_missing_field_is_a_clean_400(self, client, db, make_user, token_for):
        user = make_user(UserRole.CONTRACTOR, "9200000002")
        resp = client.post(
            "/api/calculators/steel",
            json={"diameterMm": 12},
            headers={"Authorization": f"Bearer {token_for(user)}"},
        )
        assert resp.status_code == 400
