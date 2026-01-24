import os

from dotenv import load_dotenv


load_dotenv()


HONEYPOT_API_KEY = os.getenv("HONEYPOT_API_KEY", "")
