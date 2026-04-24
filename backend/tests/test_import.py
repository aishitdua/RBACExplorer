import pytest


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
        files={"file": ("test.yaml", malformed_yaml, "text/yaml")},
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


@pytest.mark.slow
async def test_csv_import_rejects_oversized_file(client):
    """SEC-008/016: Streaming byte-count enforces 2MB limit, ignoring Content-Length."""
    await client.post("/api/v1/projects", json={"name": "Test"})

    # Create a ~3MB payload (exceeds 2MB limit)
    header = b"method,path,description\n"
    row = b"GET,/api/v1/resource,description\n"
    # Build enough rows to exceed 2MB
    large_csv = header + row * (3 * 1024 * 1024 // len(row) + 1)

    r = await client.post(
        "/api/v1/projects/test/import/csv",
        files={"file": ("large.csv", large_csv, "text/csv")},
    )
    assert r.status_code == 413
    assert "too large" in r.json()["detail"].lower()


async def test_csv_import_rejects_unsupported_content_type(client):
    """SEC-008/016: Content-type allowlist blocks non-CSV uploads."""
    await client.post("/api/v1/projects", json={"name": "Test"})

    csv_data = b"method,path\nGET,/api/v1/users\n"
    r = await client.post(
        "/api/v1/projects/test/import/csv",
        files={"file": ("data.json", csv_data, "application/json")},
    )
    assert r.status_code == 415
    assert "Unsupported file type" in r.json()["detail"]


async def test_yaml_import_rejects_unsupported_content_type(client):
    """SEC-008/016: Content-type allowlist blocks non-YAML uploads for YAML endpoint."""
    await client.post("/api/v1/projects", json={"name": "Test"})

    yaml_data = b"admin:\n  users:\n    list: List users\n"
    r = await client.post(
        "/api/v1/projects/test/import/yaml",
        files={"file": ("data.json", yaml_data, "application/json")},
    )
    assert r.status_code == 415
    assert "Unsupported file type" in r.json()["detail"]
