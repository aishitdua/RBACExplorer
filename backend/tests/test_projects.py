import pytest


async def test_create_project_auto_slug(client):
    r = await client.post("/api/v1/projects", json={"name": "My SaaS App"})
    assert r.status_code == 201
    data = r.json()
    assert data["slug"] == "my-saas-app"
    assert data["name"] == "My SaaS App"


async def test_create_project_custom_slug(client):
    r = await client.post("/api/v1/projects", json={"name": "App", "slug": "custom-slug"})
    assert r.status_code == 201
    assert r.json()["slug"] == "custom-slug"


async def test_get_project(client):
    await client.post("/api/v1/projects", json={"name": "Test"})
    r = await client.get("/api/v1/projects/test")
    assert r.status_code == 200
    assert r.json()["name"] == "Test"


async def test_get_project_not_found(client):
    r = await client.get("/api/v1/projects/nonexistent")
    assert r.status_code == 404


async def test_delete_project(client):
    await client.post("/api/v1/projects", json={"name": "Delete Me"})
    r = await client.delete("/api/v1/projects/delete-me")
    assert r.status_code == 204
    r2 = await client.get("/api/v1/projects/delete-me")
    assert r2.status_code == 404
