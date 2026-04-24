async def test_import_openapi_creates_resources(client):
    await client.post("/api/v1/projects", json={"name": "Test"})
    openapi = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {"get": {}, "post": {}},
            "/users/{id}": {"get": {}, "delete": {}},
        },
    }
    r = await client.post("/api/v1/projects/test/import/openapi", json=openapi)
    assert r.status_code == 200
    assert r.json()["created"] == 4
    # second import skips existing
    r2 = await client.post("/api/v1/projects/test/import/openapi", json=openapi)
    assert r2.json()["skipped"] == 4
