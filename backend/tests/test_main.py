from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app  # Absolute import from the app directory

client = TestClient(app)

def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_lifespan():
    with patch("app.main.init_db_pool", new_callable=AsyncMock), \
         patch("app.main.close_db_pool", new_callable=AsyncMock):

        with TestClient(app):
            pass

def test_users_table_created_on_startup():
    mock_conn = AsyncMock()

    mock_acquire = AsyncMock()
    mock_acquire.__aenter__.return_value = mock_conn
    mock_acquire.__aexit__.return_value = None

    mock_pool = MagicMock()
    mock_pool.acquire.return_value = mock_acquire

    with patch("app.main.pool", mock_pool), \
         patch("app.main.init_db_pool", new_callable=AsyncMock), \
         patch("app.main.close_db_pool", new_callable=AsyncMock):

        with TestClient(app):
            pass

    mock_conn.execute.assert_called_once()