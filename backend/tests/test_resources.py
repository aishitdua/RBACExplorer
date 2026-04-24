import pytest


@pytest.fixture
async def setup(client):
    await client.post("/api/v1/projects", json={"name": "Test"})
    r_perm = await client.post(
        "/api/v1/projects/test/permissions", json={"name": "read_users"}
    )
    r_res = await client.post(
        "/api/v1/projects/test/resources", json={"method": "GET", "path": "/users"}
    )
    return {"perm_id": r_perm.json()["id"], "res_id": r_res.json()["id"]}


async def test_create_resource(client, setup):
    r = await client.post(
        "/api/v1/projects/test/resources", json={"method": "POST", "path": "/users"}
    )
    assert r.status_code == 201
    assert r.json()["method"] == "POST"


async def test_map_resource_to_permission(client, setup):
    perm_id = setup["perm_id"]
    res_id = setup["res_id"]
    r = await client.post(
        f"/api/v1/projects/test/permissions/{perm_id}/resources/{res_id}"
    )
    assert r.status_code == 200


async def test_unmap_resource_from_permission(client, setup):
    perm_id = setup["perm_id"]
    res_id = setup["res_id"]
    await client.post(f"/api/v1/projects/test/permissions/{perm_id}/resources/{res_id}")
    r = await client.delete(
        f"/api/v1/projects/test/permissions/{perm_id}/resources/{res_id}"
    )
    assert r.status_code == 204
