import os
from dotenv import dotenv_values

environment : dict = dotenv_values()

MAIN_DIR = os.path.dirname(__file__)
SYSTEMLOGS_DIR = os.path.join(MAIN_DIR, 'systemlogs')

MAX_BACKUPS = 4 
MAX_LOG_SIZE = 5 * 1024 * 1024  

UVICORN_HOST_IP = environment["API_HOST_IP"] 
UVICORN_HOST_PORT = int(environment["API_HOST_PORT"])

IBT = "a"
