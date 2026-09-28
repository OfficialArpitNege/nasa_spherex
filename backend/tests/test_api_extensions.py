import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)

def test_preview_endpoint_not_found():
    response = client.get("/api/preview/nonexistent_file_12345.png")
    assert response.status_code == 404

def test_preview_endpoint_found(tmp_path, monkeypatch):
    cache_dir = Path(settings.CACHE_DIR)
    previews_dir = cache_dir / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)
    test_file = previews_dir / "test_preview_sample.png"
    test_file.write_bytes(b"\x89PNG\r\n\x1a\nfakeimagecontent")
    try:
        response = client.get(f"/api/preview/{test_file.name}")
        assert response.status_code == 200
        assert response.content == b"\x89PNG\r\n\x1a\nfakeimagecontent"
    finally:
        if test_file.exists():
            test_file.unlink()

def test_known_object_endpoint_schema():
    # If network/data is present or cached, this returns 200 and KnownObjectValidationResponse
    # Otherwise if IRSA is unreachable, it raises 502
    response = client.get("/api/known-object/3i-atlas")
    assert response.status_code in [200, 502]
    if response.status_code == 200:
        data = response.json()
        assert data["target_name"] == "3I/ATLAS"
        assert "epoch_1" in data
        assert "epoch_2" in data
        assert "two_epoch_motion_measurable" in data
        assert "scientific_disclaimer" in data
