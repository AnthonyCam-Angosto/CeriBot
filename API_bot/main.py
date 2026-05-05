import os
from dotenv import load_dotenv

# Charger le .env AVANT tout import
load_dotenv()

from api import api

api.start()