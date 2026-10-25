"""
The complete Civil Engineering Toolkit from the spec, as pure functions.
Every formula here matches what was verified correct in the original
codebase review (D^2/162.28 for steel, 1.54x dry-volume factor for
concrete, 1.33x for plaster/mortar) and what shipped in the frontend
prototype -- ported here as the authoritative, independently unit-tested
version rather than logic embedded only in a frontend file.

Each function takes plain numbers and returns a plain dict -- no Flask,
no request parsing, no database -- so app/routes/calculators.py is a thin
validation + serialization wrapper around these, and they're testable
without spinning up the app at all.
"""

MIX_RATIOS = {
    "M10": (1, 3, 6),
    "M15": (1, 2, 4),
    "M20": (1, 1.5, 3),
    "M25": (1, 1, 2),
}

BRICK_SIZES_MM = {
    "modular": (190, 90, 90),
    "traditional": (230, 110, 75),
}

STRUCTURAL_STEEL_RATIO = {
    "slab": 0.010,
    "beam": 0.015,
    "column": 0.020,
    "footing": 0.008,
}


def concrete_quantities(length_m: float, width_m: float, thickness_m: float, mix: str) -> dict:
    if mix not in MIX_RATIOS:
        raise ValueError(f"mix must be one of {sorted(MIX_RATIOS)}.")
    c, s, a = MIX_RATIOS[mix]
    wet_volume = length_m * width_m * thickness_m
    dry_volume = wet_volume * 1.54
    total_parts = c + s + a
    cement_vol = dry_volume * (c / total_parts)
    sand_vol = dry_volume * (s / total_parts)
    agg_vol = dry_volume * (a / total_parts)
    cement_weight_kg = cement_vol * 1440
    return {
        "wetVolumeM3": round(wet_volume, 3),
        "dryVolumeM3": round(dry_volume, 3),
        "cementWeightKg": round(cement_weight_kg, 1),
        "cementBags": int((cement_weight_kg / 50) + 0.999),  # ceil without importing math
        "sandVolumeM3": round(sand_vol, 3),
        "aggregateVolumeM3": round(agg_vol, 3),
    }


def steel_weight(diameter_mm: float, length_m: float, quantity: int) -> dict:
    unit_weight_kg_per_m = (diameter_mm ** 2) / 162.28
    bar_weight_kg = unit_weight_kg_per_m * length_m
    total_weight_kg = bar_weight_kg * quantity
    return {
        "unitWeightKgPerM": round(unit_weight_kg_per_m, 4),
        "barWeightKg": round(bar_weight_kg, 3),
        "totalWeightKg": round(total_weight_kg, 2),
        "totalWeightTonnes": round(total_weight_kg / 1000, 4),
    }


def brick_quantities(
    wall_length_m: float,
    wall_height_m: float,
    wall_thickness_m: float,
    brick_size: str,
    mortar_thickness_mm: float,
) -> dict:
    if brick_size not in BRICK_SIZES_MM:
        raise ValueError(f"brick_size must be one of {sorted(BRICK_SIZES_MM)}.")
    brick_l, brick_w, brick_h = BRICK_SIZES_MM[brick_size]
    wall_volume = wall_length_m * wall_height_m * wall_thickness_m

    with_mortar_l = (brick_l + mortar_thickness_mm) / 1000
    with_mortar_w = (brick_w + mortar_thickness_mm) / 1000
    with_mortar_h = (brick_h + mortar_thickness_mm) / 1000
    brick_with_mortar_vol = with_mortar_l * with_mortar_w * with_mortar_h
    num_bricks = wall_volume / brick_with_mortar_vol

    actual_brick_vol = (brick_l / 1000) * (brick_w / 1000) * (brick_h / 1000)
    mortar_volume = wall_volume - (num_bricks * actual_brick_vol)
    dry_mortar_volume = mortar_volume * 1.33
    cement_vol = dry_mortar_volume * (1 / 7)  # 1:6 mortar mix
    sand_vol = dry_mortar_volume * (6 / 7)
    cement_weight_kg = cement_vol * 1440

    return {
        "wallVolumeM3": round(wall_volume, 3),
        "bricksRequired": int(num_bricks + 0.999),
        "mortarVolumeM3": round(mortar_volume, 4),
        "cementBags": int((cement_weight_kg / 50) + 0.999),
        "sandVolumeM3": round(sand_vol, 3),
    }


def plaster_quantities(area_m2: float, thickness_m: float, mix: str) -> dict:
    ratios = {"1:4": (1, 4), "1:6": (1, 6)}
    if mix not in ratios:
        raise ValueError("mix must be '1:4' or '1:6'.")
    c, s = ratios[mix]
    wet_volume = area_m2 * thickness_m
    dry_volume = wet_volume * 1.33
    total = c + s
    cement_vol = dry_volume * (c / total)
    sand_vol = dry_volume * (s / total)
    cement_weight_kg = cement_vol * 1440
    return {
        "wetVolumeM3": round(wet_volume, 4),
        "dryVolumeM3": round(dry_volume, 4),
        "cementBags": int((cement_weight_kg / 50) + 0.999),
        "sandVolumeM3": round(sand_vol, 3),
    }


def excavation_quantities(
    length_m: float, width_m: float, depth_m: float, bulking_pct: float
) -> dict:
    bank_volume = length_m * width_m * depth_m
    bulked_volume = bank_volume * (1 + bulking_pct / 100)
    truck_loads = bulked_volume / 6  # standard 6 m3 tipper
    return {
        "bankVolumeM3": round(bank_volume, 3),
        "bulkedVolumeM3": round(bulked_volume, 3),
        "tipperTruckLoads": int(truck_loads + 0.999),
    }


def structural_quantities(
    element: str, length_m: float, width_m: float, height_m: float, count: int
) -> dict:
    element = element.lower()
    if element not in STRUCTURAL_STEEL_RATIO:
        raise ValueError(f"element must be one of {sorted(STRUCTURAL_STEEL_RATIO)}.")
    single_volume = length_m * width_m * height_m
    total_volume = single_volume * count
    steel_ratio = STRUCTURAL_STEEL_RATIO[element]
    steel_weight_kg = total_volume * steel_ratio * 7850  # steel density kg/m3
    dry_volume = total_volume * 1.54
    cement_vol = dry_volume * (1 / 5.5)  # M20-equivalent 1:1.5:3
    cement_weight_kg = cement_vol * 1440
    return {
        "singleVolumeM3": round(single_volume, 4),
        "totalVolumeM3": round(total_volume, 3),
        "cementBags": int((cement_weight_kg / 50) + 0.999),
        "steelWeightKg": round(steel_weight_kg, 1),
        "steelWeightTonnes": round(steel_weight_kg / 1000, 3),
        "reinforcementRatioPct": round(steel_ratio * 100, 1),
    }
