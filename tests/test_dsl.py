import pytest

from sgmp.dsl import QueryError, to_sql, validate

OK = {"op": "list", "planning_area": "BISHAN"}


@pytest.mark.parametrize("bad", [
    "SELECT 1",
    {"op": "drop", "planning_area": "BISHAN"},
    {"op": "list", "planning_area": "BISHAN", "sql": "DROP TABLE x"},
    {"op": "list", "planning_area": "TAMPINES"},
    {"op": "list", "subzone": "NOWHERE"},
    {"op": "list", "planning_area": "BISHAN", "land_use": ["CASINO"]},
    {"op": "list", "planning_area": "BISHAN", "land_use": []},
    {"op": "list", "planning_area": "BISHAN", "gpr": {"cmp": "!=", "value": 3}},
    {"op": "list", "planning_area": "BISHAN", "gpr": {"cmp": ">", "value": "3; drop"}},
    {"op": "list", "planning_area": "BISHAN", "gpr": {"cmp": ">", "value": 31}},
    {"op": "list", "planning_area": "BISHAN", "gpr": {"cmp": ">", "value": -1}},
    {"op": "list", "near": {"station": "ORCHARD", "radius_m": 400}},
    {"op": "list", "near": {"station": "BISHAN", "radius_m": 5000}},
    {"op": "list", "near": {"station": "BISHAN", "radius_m": 10}},
    {"op": "list", "near": {"station": "BISHAN", "radius_m": 400, "x": 1}},
    {"op": "list", "land_use": ["WHITE"]},
    {"op": "count", "planning_area": "BISHAN", "sort": "area_desc"},
    {"op": "count", "planning_area": "BISHAN", "limit": 5},
    {"op": "list", "planning_area": "BISHAN", "sort": "random"},
    {"op": "list", "planning_area": "BISHAN", "limit": 0},
    {"op": "list", "planning_area": "BISHAN", "limit": 501},
])
def test_validator_rejects(bad):
    with pytest.raises(QueryError):
        validate(bad)


def test_validator_normalises():
    q = validate({"op": "list", "near": {"station": "Bishan MRT Station"},
                  "land_use": ["white", "WHITE"], "limit": "5"})
    assert q["near"] == {"station": "BISHAN", "radius_m": 400.0}
    assert q["land_use"] == ["WHITE"]
    assert q["limit"] == 5


def test_validator_boundaries_accepted():
    validate({"op": "list", "near": {"station": "BISHAN", "radius_m": 50}})
    validate({"op": "list", "near": {"station": "BISHAN", "radius_m": 2000}})
    validate({"op": "list", "planning_area": "BISHAN", "limit": 1})
    validate({"op": "list", "planning_area": "BISHAN", "limit": 500})
    validate({"op": "list", "planning_area": "BISHAN", "gpr": {"cmp": ">=", "value": 0}})


def test_refuse_passthrough():
    assert validate({"op": "refuse", "reason": "x"}) == {"op": "refuse", "reason": "x"}


def test_sql_rendering_shows_every_filter():
    q = validate({"op": "list", "planning_area": "BISHAN", "land_use": ["RESIDENTIAL"],
                  "gpr": {"cmp": ">", "value": 3}, "sort": "area_desc", "limit": 5})
    s = to_sql(q)
    assert "planning_area = 'BISHAN'" in s
    assert "lu_desc IN ('RESIDENTIAL')" in s
    assert "gpr_numeric > 3" in s
    assert "ORDER BY area_m2 DESC" in s and "LIMIT 5" in s
    near = to_sql(validate({"op": "total_area", "near": {"station": "BISHAN", "radius_m": 400}}))
    assert "ST_Intersection" in near and "400 m around BISHAN" in near
    assert "GROUP BY lu_desc" in to_sql(validate({"op": "breakdown", "planning_area": "BISHAN"}))
