import pytest


@pytest.fixture
async def project_with_orphan(client):
    await client.post("/api/v1/projects", json={"name": "Test"})
    # orphaned permission — not assigned to any role
    await client.post(
        "/api/v1/projects/test/permissions", json={"name": "orphaned_perm"}
    )


async def test_detects_orphaned_permission(client, project_with_orphan):
    r = await client.get("/api/v1/projects/test/analyze")
    assert r.status_code == 200
    findings = r.json()["findings"]
    assert any(f["type"] == "orphaned_permission" for f in findings)


async def test_detects_empty_role(client):
    await client.post("/api/v1/projects", json={"name": "Test"})
    await client.post("/api/v1/projects/test/roles", json={"name": "empty"})
    r = await client.get("/api/v1/projects/test/analyze")
    findings = r.json()["findings"]
    assert any(f["type"] == "empty_role" for f in findings)


async def test_analyze_redundant_assignment_scoped_to_project(client):
    """
    Redundant assignment detection must be project-scoped: findings in one project
    must not appear in another, even when both have similar inheritance structures.
    """
    # Project A: child_a inherits parent_a, both have 'read' → 1 redundant finding
    await client.post("/api/v1/projects", json={"name": "A"})
    parent_a = (
        await client.post("/api/v1/projects/a/roles", json={"name": "parent"})
    ).json()
    child_a = (
        await client.post("/api/v1/projects/a/roles", json={"name": "child"})
    ).json()
    perm_a = (
        await client.post("/api/v1/projects/a/permissions", json={"name": "read"})
    ).json()
    await client.post(
        f"/api/v1/projects/a/roles/{child_a['id']}/permissions/{perm_a['id']}"
    )
    await client.post(
        f"/api/v1/projects/a/roles/{parent_a['id']}/permissions/{perm_a['id']}"
    )
    await client.post(
        f"/api/v1/projects/a/roles/{child_a['id']}/parents",
        json={"parent_role_id": parent_a["id"]},
    )

    # Project B: mirror structure — child_b inherits parent_b, both have 'read'
    # → 1 redundant finding
    await client.post("/api/v1/projects", json={"name": "B"})
    parent_b = (
        await client.post("/api/v1/projects/b/roles", json={"name": "parent_b"})
    ).json()
    child_b = (
        await client.post("/api/v1/projects/b/roles", json={"name": "child_b"})
    ).json()
    perm_b = (
        await client.post("/api/v1/projects/b/permissions", json={"name": "read"})
    ).json()
    await client.post(
        f"/api/v1/projects/b/roles/{child_b['id']}/permissions/{perm_b['id']}"
    )
    await client.post(
        f"/api/v1/projects/b/roles/{parent_b['id']}/permissions/{perm_b['id']}"
    )
    await client.post(
        f"/api/v1/projects/b/roles/{child_b['id']}/parents",
        json={"parent_role_id": parent_b["id"]},
    )

    # Project A: exactly 1 redundant_assignment for "child" — not contaminated by B
    r_a = await client.get("/api/v1/projects/a/analyze")
    assert r_a.status_code == 200
    redundant_a = [
        f for f in r_a.json()["findings"] if f["type"] == "redundant_assignment"
    ]
    assert len(redundant_a) == 1
    assert redundant_a[0]["detail"]["role_name"] == "child"

    # Project B: exactly 1 redundant_assignment for "child_b" — not contaminated by A
    r_b = await client.get("/api/v1/projects/b/analyze")
    assert r_b.status_code == 200
    redundant_b = [
        f for f in r_b.json()["findings"] if f["type"] == "redundant_assignment"
    ]
    assert len(redundant_b) == 1
    assert redundant_b[0]["detail"]["role_name"] == "child_b"
