import os
from dotenv import load_dotenv
load_dotenv()
DATABASE_URL=os.getenv('DATABASE_URL')
SECRET_KEY=os.getenv('SECRET_KEY','dev-secret')
APP_ENV=os.getenv('APP_ENV','local')
if not DATABASE_URL:
    raise RuntimeError('Missing DATABASE_URL in .env')
