# tests/conftest.py
import pytest
import requests
import threading
import time
from http.server import HTTPServer
from api.server import RequestHandler

BASE_URL = "http://localhost:8000"


@pytest.fixture(scope="session")
def api_server():
    """Start the API server once for the whole test session."""
    server = HTTPServer(("localhost", 8000), RequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.5)  # wait for server to boot
    yield BASE_URL
    server.shutdown()