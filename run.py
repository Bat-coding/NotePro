from app import create_app
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Verify important environment variables
print(f"DATABASE_URL: {os.getenv('DATABASE_URL')}")

app = create_app()

if __name__ == '__main__':
    # Running on localhost (host machine)
    app.run(host='127.0.0.1', port=5000, debug=True)
