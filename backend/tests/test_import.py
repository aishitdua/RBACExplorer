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


async def test_yaml_import_handles_errors_securely(client):
    """SEC-006: Verify 500 responses do not expose raw exception details."""
    await client.post("/api/v1/projects", json={"name": "Test"})

    # YAML that is not a valid dictionary at the root level
    # This triggers the "YAML root must be a dictionary" check
    malformed_yaml = b"""
- item1
- item2
"""
    r = await client.post(
        "/api/v1/projects/test/import/yaml",
        files={"file": ("test.yaml", malformed_yaml)},
    )

    assert r.status_code == 500
    detail = r.json()["detail"]

    # Verify the response uses the generic message, not raw exception
    assert detail == "Import failed. Check your YAML structure and try again."

    # Ensure no raw exception class names or strings are exposed
    assert "ValidationError" not in detail
    assert "IntegrityError" not in detail
    assert "Traceback" not in detail
    assert "str(e)" not in detail
