import os
from dotenv import dotenv_values

environment : dict = dotenv_values()

MAIN_DIR = os.path.dirname(__file__)
SYSTEMLOGS_DIR = os.path.join(MAIN_DIR, 'systemlogs')

MAX_BACKUPS = 4 
MAX_LOG_SIZE = 5 * 1024 * 1024  

UVICORN_HOST_IP = environment.get("API_HOST_IP") or os.getenv("API_HOST_IP", "0.0.0.0")
UVICORN_HOST_PORT = int(environment.get("API_HOST_PORT") or os.getenv("API_HOST_PORT", "8000"))

FERNET_KEY = environment.get("FERNET_KEY") or os.getenv("FERNET_KEY", "") 
