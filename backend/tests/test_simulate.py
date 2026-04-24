import pytest


@pytest.fixture
async def rbac(client):
    """
    Sets up: admin -> editor (inheritance), read_users perm -> GET /users resource,
    assigned to editor
    """
    await client.post("/api/v1/projects", json={"name": "Test"})
    r_admin = await client.post("/api/v1/projects/test/roles", json={"name": "admin"})
    r_editor = await client.post("/api/v1/projects/test/roles", json={"name": "editor"})
    admin_id = r_admin.json()["id"]
    editor_id = r_editor.json()["id"]
    # editor inherits from admin
    await client.post(
        f"/api/v1/projects/test/roles/{editor_id}/parents",
        json={"parent_role_id": admin_id},
    )
    # permission
    r_perm = await client.post(
        "/api/v1/projects/test/permissions", json={"name": "read_users"}
    )
    perm_id = r_perm.json()["id"]
    # resource
    r_res = await client.post(
        "/api/v1/projects/test/resources", json={"method": "GET", "path": "/users"}
    )
    res_id = r_res.json()["id"]
    # map permission -> resource
    await client.post(f"/api/v1/projects/test/permissions/{perm_id}/resources/{res_id}")
    # assign permission to admin role only
    await client.post(f"/api/v1/projects/test/roles/{admin_id}/permissions/{perm_id}")
    return {
        "admin_id": admin_id,
        "editor_id": editor_id,
        "perm_id": perm_id,
        "res_id": res_id,
    }


async def test_simulate_direct_permission(client, rbac):
    r = await client.get(f"/api/v1/projects/test/simulate/{rbac['admin_id']}")
    assert r.status_code == 200
    data = r.json()
    allowed = [res for res in data["resources"] if res["allowed"]]
    assert any(res["path"] == "/users" for res in allowed)


async def test_simulate_inherited_permission(client, rbac):
    """Editor should have access to GET /users via inheritance from admin"""
    r = await client.get(f"/api/v1/projects/test/simulate/{rbac['editor_id']}")
    assert r.status_code == 200
    data = r.json()
    allowed = [res for res in data["resources"] if res["allowed"]]
    assert any(res["path"] == "/users" for res in allowed)


async def test_simulate_no_access(client, rbac):
    """A role with no permissions and no parents sees everything as denied"""
    r_viewer = await client.post("/api/v1/projects/test/roles", json={"name": "viewer"})
    viewer_id = r_viewer.json()["id"]
    r = await client.get(f"/api/v1/projects/test/simulate/{viewer_id}")
    assert r.status_code == 200
    denied = [res for res in r.json()["resources"] if not res["allowed"]]
    assert len(denied) == 1
