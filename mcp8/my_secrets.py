import os
from dotenv import load_dotenv

load_dotenv()

class Secrets():
    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_api_model = os.getenv("GEMINI_API_MODEL")
        self.gemini_base_url = os.getenv("GEMINI_BASE_URL")

        self.mongo_uri = os.getenv("MONGODB_URI")
        self.mongo_db = os.getenv("DB")
        self.books_col = os.getenv("BOOKS_COL")
        self.members_col = os.getenv("MEMBERS_COL")