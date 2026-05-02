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
    Redundant assignment detection must work correctly per project and must not
    return findings from other projects.
    """
    # Project A: child inherits from parent, both have 'read' permission → redundant
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

    # Project B: completely separate, no redundancy
    await client.post("/api/v1/projects", json={"name": "B"})

    r = await client.get("/api/v1/projects/a/analyze")
    assert r.status_code == 200
    findings = r.json()["findings"]
    redundant = [f for f in findings if f["type"] == "redundant_assignment"]
    assert len(redundant) == 1
    assert redundant[0]["detail"]["role_name"] == "child"

    # Project B should have zero findings
    r2 = await client.get("/api/v1/projects/b/analyze")
    assert r2.status_code == 200
    assert r2.json()["findings"] == []
