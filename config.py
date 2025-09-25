import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Default user agent string - SEC requires real contact information
DEFAULT_USER_AGENT = "SEC Filing Tracker contact@example.com"

# Get user agent from environment variable with fallback to default
USER_AGENT = os.getenv('SEC_USER_AGENT', DEFAULT_USER_AGENT)

# Get OPEN ROUTER API key from environment variable
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

# Function to get user agent (for consistency across modules)
def get_user_agent():
    """Get the user agent string from environment variable or use default"""
    # Import here to avoid circular imports
    try:
        from api_key_utils import ensure_sec_user_agent
        # Only prompt if we're using the default
        if USER_AGENT == DEFAULT_USER_AGENT:
            user_agent = ensure_sec_user_agent()
            return user_agent
        return USER_AGENT
    except ImportError:
        return USER_AGENT

# Function to get OPEN ROUTER API key
def get_openrouter_api_key():
    """Get the OPEN ROUTER API key from environment variable"""
    # Import here to avoid circular imports
    try:
        from api_key_utils import ensure_openrouter_api_key
        # Only prompt if we don't have a key
        if not OPENROUTER_API_KEY:
            return ensure_openrouter_api_key()
        return OPENROUTER_API_KEY
    except ImportError:
        return OPENROUTER_API_KEY