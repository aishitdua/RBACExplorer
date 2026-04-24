async def test_create_project_auto_slug(client):
    r = await client.post("/api/v1/projects", json={"name": "My SaaS App"})
    assert r.status_code == 201
    data = r.json()
    assert data["slug"] == "my-saas-app"
    assert data["name"] == "My SaaS App"


async def test_create_project_custom_slug(client):
    r = await client.post(
        "/api/v1/projects", json={"name": "App", "slug": "custom-slug"}
    )
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


async def test_create_project_duplicate_slug(client):
    await client.post("/api/v1/projects", json={"name": "My App"})
    r = await client.post("/api/v1/projects", json={"name": "My App"})
    assert r.status_code == 400


async def test_delete_project_not_found(client):
    r = await client.delete("/api/v1/projects/does-not-exist")
    assert r.status_code == 404


# --- SEC-007: Field constraint tests ---


async def test_create_project_name_too_long(client):
    r = await client.post("/api/v1/projects", json={"name": "a" * 129})
    assert r.status_code == 422


async def test_create_project_invalid_slug(client):
    r = await client.post(
        "/api/v1/projects", json={"name": "App", "slug": "Invalid Slug!"}
    )
    assert r.status_code == 422


# --- SEC-010: Clean endpoint confirmation tests ---


async def test_clean_project_wrong_confirm_slug(client):
    """Calling /clean with wrong confirm slug should return 400"""
    await client.post("/api/v1/projects", json={"name": "Test Project"})
    r = await client.post(
        "/api/v1/projects/test-project/clean", json={"confirm": "wrong-slug"}
    )
    assert r.status_code == 400
    assert "Confirmation slug does not match" in r.json()["detail"]


async def test_clean_project_correct_confirm_slug(client):
    """Calling /clean with correct confirm slug should wipe data"""
    # Create a project with roles, permissions, and resources
    await client.post("/api/v1/projects", json={"name": "Test Project"})
    slug = "test-project"

    # Add a role
    await client.post(
        f"/api/v1/projects/{slug}/roles",
        json={"name": "Admin", "description": "Admin role"},
    )

    # Add a permission
    await client.post(
        f"/api/v1/projects/{slug}/permissions",
        json={"name": "users.read", "description": "Read users"},
    )

    # Add a resource
    await client.post(
        f"/api/v1/projects/{slug}/resources",
        json={"method": "GET", "path": "/api/users", "description": "Get users"},
    )

    # Verify data exists
    r_get = await client.get(f"/api/v1/projects/{slug}/roles")
    assert len(r_get.json()) == 1

    # Clean the project with correct confirmation
    r_clean = await client.post(
        f"/api/v1/projects/{slug}/clean", json={"confirm": slug}
    )
    assert r_clean.status_code == 204

    # Verify data is wiped
    r_roles = await client.get(f"/api/v1/projects/{slug}/roles")
    assert r_roles.json() == []

    r_perms = await client.get(f"/api/v1/projects/{slug}/permissions")
    assert r_perms.json() == []

    r_ress = await client.get(f"/api/v1/projects/{slug}/resources")
    assert r_ress.json() == []


async def test_clean_project_no_body_validation_error(client):
    """Calling /clean with no body should return 422 (Pydantic validation)"""
    await client.post("/api/v1/projects", json={"name": "Test Project"})
    r = await client.post("/api/v1/projects/test-project/clean")
    assert r.status_code == 422
