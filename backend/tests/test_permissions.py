import pytest


@pytest.fixture
async def setup(client):
    await client.post("/api/v1/projects", json={"name": "Test"})
    r_role = await client.post("/api/v1/projects/test/roles", json={"name": "admin"})
    r_perm = await client.post(
        "/api/v1/projects/test/permissions", json={"name": "read_users"}
    )
    return {"role_id": r_role.json()["id"], "perm_id": r_perm.json()["id"]}


async def test_create_permission(client, setup):
    r = await client.post(
        "/api/v1/projects/test/permissions", json={"name": "delete_users"}
    )
    assert r.status_code == 201
    assert r.json()["name"] == "delete_users"


async def test_list_permissions(client, setup):
    r = await client.get("/api/v1/projects/test/permissions")
    assert r.status_code == 200
    assert any(p["name"] == "read_users" for p in r.json())


async def test_assign_permission_to_role(client, setup):
    role_id = setup["role_id"]
    perm_id = setup["perm_id"]
    r = await client.post(
        f"/api/v1/projects/test/roles/{role_id}/permissions/{perm_id}"
    )
    assert r.status_code == 200


async def test_unassign_permission_from_role(client, setup):
    role_id = setup["role_id"]
    perm_id = setup["perm_id"]
    await client.post(f"/api/v1/projects/test/roles/{role_id}/permissions/{perm_id}")
    r = await client.delete(
        f"/api/v1/projects/test/roles/{role_id}/permissions/{perm_id}"
    )
    assert r.status_code == 204


# --- SEC-002: Cross-project IDOR tests ---


@pytest.fixture
async def two_projects(client):
    """Create two projects, each with a role, permission, and resource."""
    await client.post("/api/v1/projects", json={"name": "Alpha"})
    await client.post("/api/v1/projects", json={"name": "Beta"})

    r_role_a = await client.post(
        "/api/v1/projects/alpha/roles", json={"name": "role-a"}
    )
    r_perm_a = await client.post(
        "/api/v1/projects/alpha/permissions", json={"name": "perm-a"}
    )
    r_res_a = await client.post(
        "/api/v1/projects/alpha/resources", json={"method": "GET", "path": "/res-a"}
    )

    r_role_b = await client.post("/api/v1/projects/beta/roles", json={"name": "role-b"})
    r_perm_b = await client.post(
        "/api/v1/projects/beta/permissions", json={"name": "perm-b"}
    )
    r_res_b = await client.post(
        "/api/v1/projects/beta/resources", json={"method": "GET", "path": "/res-b"}
    )

    return {
        "role_a": r_role_a.json()["id"],
        "perm_a": r_perm_a.json()["id"],
        "res_a": r_res_a.json()["id"],
        "role_b": r_role_b.json()["id"],
        "perm_b": r_perm_b.json()["id"],
        "res_b": r_res_b.json()["id"],
    }


async def test_assign_permission_cross_project_role_rejected(client, two_projects):
    """assign_permission: role from project B used under project A's slug → 404."""
    role_b = two_projects["role_b"]
    perm_a = two_projects["perm_a"]
    r = await client.post(f"/api/v1/projects/alpha/roles/{role_b}/permissions/{perm_a}")
    assert r.status_code == 404


async def test_assign_permission_cross_project_perm_rejected(client, two_projects):
    """assign_permission: permission from project B under project A's slug → 404."""
    role_a = two_projects["role_a"]
    perm_b = two_projects["perm_b"]
    r = await client.post(f"/api/v1/projects/alpha/roles/{role_a}/permissions/{perm_b}")
    assert r.status_code == 404


async def test_unassign_permission_cross_project_rejected(client, two_projects):
    """unassign_permission: foreign role ID under project A's slug → 404."""
    role_b = two_projects["role_b"]
    perm_a = two_projects["perm_a"]
    r = await client.delete(
        f"/api/v1/projects/alpha/roles/{role_b}/permissions/{perm_a}"
    )
    assert r.status_code == 404


async def test_map_resource_cross_project_perm_rejected(client, two_projects):
    """map_resource: permission from project B used under project A's slug → 404."""
    perm_b = two_projects["perm_b"]
    res_a = two_projects["res_a"]
    r = await client.post(
        f"/api/v1/projects/alpha/permissions/{perm_b}/resources/{res_a}"
    )
    assert r.status_code == 404


async def test_map_resource_cross_project_res_rejected(client, two_projects):
    """map_resource: resource from project B used under project A's slug → 404."""
    perm_a = two_projects["perm_a"]
    res_b = two_projects["res_b"]
    r = await client.post(
        f"/api/v1/projects/alpha/permissions/{perm_a}/resources/{res_b}"
    )
    assert r.status_code == 404


async def test_unmap_resource_cross_project_rejected(client, two_projects):
    """unmap_resource: foreign permission ID under project A's slug → 404."""
    perm_b = two_projects["perm_b"]
    res_a = two_projects["res_a"]
    r = await client.delete(
        f"/api/v1/projects/alpha/permissions/{perm_b}/resources/{res_a}"
    )
    assert r.status_code == 404
