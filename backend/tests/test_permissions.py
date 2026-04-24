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
