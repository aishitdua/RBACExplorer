import pytest


@pytest.fixture
async def project(client):
    r = await client.post("/api/v1/projects", json={"name": "Test"})
    return r.json()


async def test_create_role(client, project):
    r = await client.post(f"/api/v1/projects/test/roles", json={"name": "admin", "color": "#ff0000"})
    assert r.status_code == 201
    assert r.json()["name"] == "admin"


async def test_list_roles(client, project):
    await client.post("/api/v1/projects/test/roles", json={"name": "admin"})
    await client.post("/api/v1/projects/test/roles", json={"name": "viewer"})
    r = await client.get("/api/v1/projects/test/roles")
    assert r.status_code == 200
    assert len(r.json()) == 2


async def test_add_parent(client, project):
    r1 = await client.post("/api/v1/projects/test/roles", json={"name": "admin"})
    r2 = await client.post("/api/v1/projects/test/roles", json={"name": "editor"})
    admin_id = r1.json()["id"]
    editor_id = r2.json()["id"]
    r = await client.post(f"/api/v1/projects/test/roles/{editor_id}/parents", json={"parent_role_id": admin_id})
    assert r.status_code == 200


async def test_cycle_detection(client, project):
    r1 = await client.post("/api/v1/projects/test/roles", json={"name": "admin"})
    r2 = await client.post("/api/v1/projects/test/roles", json={"name": "editor"})
    admin_id = r1.json()["id"]
    editor_id = r2.json()["id"]
    # editor inherits from admin
    await client.post(f"/api/v1/projects/test/roles/{editor_id}/parents", json={"parent_role_id": admin_id})
    # making admin inherit from editor would create a cycle
    r = await client.post(f"/api/v1/projects/test/roles/{admin_id}/parents", json={"parent_role_id": editor_id})
    assert r.status_code == 400


async def test_delete_role(client, project):
    r = await client.post("/api/v1/projects/test/roles", json={"name": "temp"})
    role_id = r.json()["id"]
    r = await client.delete(f"/api/v1/projects/test/roles/{role_id}")
    assert r.status_code == 204


async def test_update_role(client, project):
    r = await client.post("/api/v1/projects/test/roles", json={"name": "admin"})
    role_id = r.json()["id"]
    r = await client.patch(f"/api/v1/projects/test/roles/{role_id}", json={"name": "superadmin"})
    assert r.status_code == 200
    assert r.json()["name"] == "superadmin"


async def test_remove_parent(client, project):
    r1 = await client.post("/api/v1/projects/test/roles", json={"name": "admin"})
    r2 = await client.post("/api/v1/projects/test/roles", json={"name": "editor"})
    admin_id = r1.json()["id"]
    editor_id = r2.json()["id"]
    await client.post(f"/api/v1/projects/test/roles/{editor_id}/parents", json={"parent_role_id": admin_id})
    r = await client.delete(f"/api/v1/projects/test/roles/{editor_id}/parents/{admin_id}")
    assert r.status_code == 204


async def test_create_role_duplicate_name(client, project):
    await client.post("/api/v1/projects/test/roles", json={"name": "admin"})
    r = await client.post("/api/v1/projects/test/roles", json={"name": "admin"})
    assert r.status_code == 400
