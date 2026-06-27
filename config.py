import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "https://medbridge-mcp.onrender.com")
MCP_SECRET_KEY = os.getenv("MCP_SECRET_KEY", "")

SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "dev-secret-change-me")
SESSION_COOKIE_NAME = "medbridge_session"
FLASH_COOKIE_NAME = "medbridge_flash"

APP_URL = os.getenv("APP_URL", "http://localhost:8000")

MCP_HTTP_TIMEOUT = 90.0
MCP_SLOW_THRESHOLD_SECONDS = 5.0
