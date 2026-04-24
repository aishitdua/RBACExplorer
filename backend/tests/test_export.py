import pytest


@pytest.fixture
async def setup(client):
    await client.post("/api/v1/projects", json={"name": "Test"})
    await client.post("/api/v1/projects/test/roles", json={"name": "admin"})
    r_perm = await client.post(
        "/api/v1/projects/test/permissions", json={"name": "read_users"}
    )
    r_res = await client.post(
        "/api/v1/projects/test/resources", json={"method": "GET", "path": "/users"}
    )
    perm_id = r_perm.json()["id"]
    res_id = r_res.json()["id"]
    await client.post(f"/api/v1/projects/test/permissions/{perm_id}/resources/{res_id}")


async def test_export_fastapi_contains_route_stub(client, setup):
    r = await client.get("/api/v1/projects/test/export/fastapi")
    assert r.status_code == 200
    code = r.text
    assert "require_permission" in code
    assert "/users" in code
    assert "read_users" in code
