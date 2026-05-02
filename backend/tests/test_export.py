import ast

import pytest


@pytest.fixture
async def setup(client):
    await client.post("/api/v1/projects", json={"name": "Test"})
    await client.post("/api/v1/projects/test/roles", json={"name": "admin"})
    r_perm = await client.post(
        "/api/v1/projects/test/permissions", json={"name": "read_users"}
    )
    r_res = await client.post(
        "/api/v1/projects/test/resources", json={"method": "GET", "path": "/users"}
    )
    perm_id = r_perm.json()["id"]
    res_id = r_res.json()["id"]
    await client.post(f"/api/v1/projects/test/permissions/{perm_id}/resources/{res_id}")


async def test_export_fastapi_contains_route_stub(client, setup):
    r = await client.get("/api/v1/projects/test/export/fastapi")
    assert r.status_code == 200
    code = r.text
    assert "require_permission" in code
    assert "/users" in code
    assert "read_users" in code


async def test_export_fastapi_is_valid_python(client, setup):
    """The exported code must be syntactically valid Python (SEC-003)."""
    r = await client.get("/api/v1/projects/test/export/fastapi")
    assert r.status_code == 200
    # ast.parse raises SyntaxError if the output is not valid Python
    ast.parse(r.text)


async def test_resource_create_rejects_path_with_double_quote(client):
    """Schema validation must reject paths containing double-quotes (SEC-012)."""
    await client.post("/api/v1/projects", json={"name": "InjTest"})
    r = await client.post(
        "/api/v1/projects/injtest/resources",
        json={"method": "GET", "path": '/users/"injected'},
    )
    assert r.status_code == 422


async def test_resource_create_rejects_path_with_newline(client):
    """Schema validation must reject paths containing newline characters (SEC-012)."""
    await client.post("/api/v1/projects", json={"name": "InjTest2"})
    r = await client.post(
        "/api/v1/projects/injtest2/resources",
        json={"method": "GET", "path": "/users\nbackdoor"},
    )
    assert r.status_code == 422


async def test_resource_create_rejects_invalid_method(client):
    """Schema validation must reject HTTP methods not in the allowed Literal set."""
    await client.post("/api/v1/projects", json={"name": "MethodTest"})
    r = await client.post(
        "/api/v1/projects/methodtest/resources",
        json={"method": "HACK", "path": "/users"},
    )
    assert r.status_code == 422


async def test_resource_create_rejects_path_too_long(client):
    """Schema validation must reject paths exceeding 512 characters."""
    await client.post("/api/v1/projects", json={"name": "LenTest"})
    long_path = "/" + "a" * 513
    r = await client.post(
        "/api/v1/projects/lentest/resources",
        json={"method": "GET", "path": long_path},
    )
    assert r.status_code == 422


async def test_export_fastapi_deduplicates_func_names(client):
    """Paths that sanitize to the same identifier must get unique function names."""
    await client.post("/api/v1/projects", json={"name": "Test"})
    perm1 = (
        await client.post("/api/v1/projects/test/permissions", json={"name": "p1"})
    ).json()
    perm2 = (
        await client.post("/api/v1/projects/test/permissions", json={"name": "p2"})
    ).json()
    # /api/users and /api_users both sanitize to 'api_users'
    res1 = (
        await client.post(
            "/api/v1/projects/test/resources",
            json={"method": "GET", "path": "/api/users"},
        )
    ).json()
    res2 = (
        await client.post(
            "/api/v1/projects/test/resources",
            json={"method": "GET", "path": "/api_users"},
        )
    ).json()
    await client.post(
        f"/api/v1/projects/test/permissions/{perm1['id']}/resources/{res1['id']}"
    )
    await client.post(
        f"/api/v1/projects/test/permissions/{perm2['id']}/resources/{res2['id']}"
    )

    r = await client.get("/api/v1/projects/test/export/fastapi")
    assert r.status_code == 200
    code = r.text

    # Both function definitions must be present with distinct names
    assert "async def get_api_users(" in code
    assert "async def get_api_users_2(" in code

    # Generated code must be valid Python
    ast.parse(code)
