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
        # Always check if we need to prompt (when SEC_USER_AGENT env var is not set)
        if not os.getenv('SEC_USER_AGENT'):
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
        # Always check if we need to prompt (when OPENROUTER_API_KEY env var is not set)
        if not os.getenv('OPENROUTER_API_KEY'):
            return ensure_openrouter_api_key()
        return OPENROUTER_API_KEY
    except ImportError:
        return OPENROUTER_API_KEY

# Function to get model
def get_model():
    """Get the OpenRouter model to use for analysis"""
    # Import here to avoid circular imports
    try:
        from api_key_utils import get_current_model
        return get_current_model()
    except ImportError:
        model = os.getenv('OPENROUTER_MODEL')
        if not model:
            print("Warning: No model configured. Please run 'python run.py model -switch' to configure a model.")
        return model