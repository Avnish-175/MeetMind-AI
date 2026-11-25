import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database.dependencies import get_db
from app.main import app


class TestHealthEndpoints(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_root_endpoint(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["title"], "MeetMind AI")
        self.assertEqual(data["status"], "online")

    def test_app_health_endpoint(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "MeetMind AI Backend")

    def test_database_health_connected(self) -> None:
        mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: mock_db

        response = self.client.get("/health/database")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy", "database": "connected"})
        mock_db.execute.assert_called_once()

    def test_database_health_unavailable(self) -> None:
        mock_db = MagicMock()
        mock_db.execute.side_effect = SQLAlchemyError("connection refused")
        app.dependency_overrides[get_db] = lambda: mock_db

        response = self.client.get("/health/database")
        self.assertEqual(response.status_code, 503)
        data = response.json()
        self.assertEqual(data, {"status": "unhealthy", "database": "unavailable"})
        self.assertNotIn("postgresql", str(data).lower())

    def test_get_db_closes_session(self) -> None:
        mock_session = MagicMock()
        with patch("app.database.dependencies.SessionLocal", return_value=mock_session):
            gen = get_db()
            yielded = next(gen)
            self.assertIs(yielded, mock_session)
            with self.assertRaises(StopIteration):
                next(gen)
            mock_session.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
