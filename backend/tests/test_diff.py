import pytest


@pytest.fixture
async def rbac(client):
    await client.post("/api/v1/projects", json={"name": "Test"})
    r_admin = await client.post("/api/v1/projects/test/roles", json={"name": "admin"})
    r_perm = await client.post("/api/v1/projects/test/permissions", json={"name": "read_users"})
    r_res = await client.post("/api/v1/projects/test/resources", json={"method": "GET", "path": "/users"})
    perm_id = r_perm.json()["id"]
    res_id = r_res.json()["id"]
    await client.post(f"/api/v1/projects/test/permissions/{perm_id}/resources/{res_id}")
    return {"admin_id": r_admin.json()["id"], "perm_id": perm_id}


async def test_diff_shows_gained_permission(client, rbac):
    """Adding read_users to admin should appear as a gained resource"""
    admin_id = rbac["admin_id"]
    perm_id = rbac["perm_id"]
    r = await client.get(
        f"/api/v1/projects/test/diff/{admin_id}",
        params={"add_permissions": [perm_id]},
    )
    assert r.status_code == 200
    data = r.json()
    assert any(res["path"] == "/users" for res in data["gained"])
    assert data["lost"] == []
