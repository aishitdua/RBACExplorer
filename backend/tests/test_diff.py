import pytest


@pytest.fixture
async def rbac(client):
    await client.post("/api/v1/projects", json={"name": "Test"})
    r_admin = await client.post("/api/v1/projects/test/roles", json={"name": "admin"})
    r_perm = await client.post(
        "/api/v1/projects/test/permissions", json={"name": "read_users"}
    )
    r_res = await client.post(
        "/api/v1/projects/test/resources", json={"method": "GET", "path": "/users"}
    )
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


async def test_diff_rejects_cross_project_permission_ids(client, rbac):
    """Passing permission IDs from a different project should be rejected"""
    # Create a second project
    await client.post("/api/v1/projects", json={"name": "Other"})

    # Create a permission in the second project
    r_perm_other = await client.post(
        "/api/v1/projects/other/permissions", json={"name": "write_users"}
    )
    other_perm_id = r_perm_other.json()["id"]

    # Try to use the other project's permission ID in project "test"
    admin_id = rbac["admin_id"]
    r = await client.get(
        f"/api/v1/projects/test/diff/{admin_id}",
        params={"add_permissions": [other_perm_id]},
    )
    assert r.status_code == 400
    assert "do not belong to this project" in r.json()["detail"]


async def test_diff_rejects_cross_project_role_id(client, rbac):
    """Passing a role ID from a different project should be rejected"""
    # Create a second project and role
    await client.post("/api/v1/projects", json={"name": "Other"})
    r_role_other = await client.post(
        "/api/v1/projects/other/roles", json={"name": "viewer"}
    )
    other_role_id = r_role_other.json()["id"]

    # Try to diff using the other project's role ID in project "test"
    r = await client.get(
        f"/api/v1/projects/test/diff/{other_role_id}",
    )
    assert r.status_code == 404
    assert "Role not found" in r.json()["detail"]
