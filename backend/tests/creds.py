import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
ADMIN = (os.environ["ADMIN_EMAIL"], os.environ["ADMIN_PASSWORD"])
LEARNER = (os.environ["LEARNER_EMAIL"], os.environ["LEARNER_PASSWORD"])
