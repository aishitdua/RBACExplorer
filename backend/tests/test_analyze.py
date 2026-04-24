import pytest


@pytest.fixture
async def project_with_orphan(client):
    await client.post("/api/v1/projects", json={"name": "Test"})
    # orphaned permission — not assigned to any role
    await client.post("/api/v1/projects/test/permissions", json={"name": "orphaned_perm"})


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
