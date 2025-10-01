import os
from dotenv import load_dotenv

load_dotenv()

class Secrets():
    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_api_model = os.getenv("GEMINI_API_MODEL")
        self.gemini_base_url = os.getenv("GEMINI_BASE_URL")

        self.weather_api = os.getenv("WEATHER_API")
        self.weather_base_url = os.getenv("WEATHER_BASE_URL")

        self.ip_api = os.getenv("IP_API")