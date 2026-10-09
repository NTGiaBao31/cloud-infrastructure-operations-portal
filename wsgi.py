from dotenv import load_dotenv

load_dotenv(override=False)

from app import create_app

app = create_app()
