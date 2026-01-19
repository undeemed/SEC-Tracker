import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# SECURITY: No hardcoded defaults - require explicit configuration
# Get user agent from environment variable (required for SEC API)
USER_AGENT = os.getenv('SEC_USER_AGENT')

# Get OPEN ROUTER API key from environment variable
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

def get_user_agent():
    """
    Get the user agent string from environment variable.
    SEC requires a valid contact email for API access.
    
    Returns:
        str: User agent string
        
    Note:
        Will prompt user interactively if not configured.
    """
    # Import here to avoid circular imports
    try:
        from utils.api_keys import ensure_sec_user_agent
        # Check if we need to prompt (when SEC_USER_AGENT env var is not set)
        if not os.getenv('SEC_USER_AGENT'):
            return ensure_sec_user_agent()
        return USER_AGENT
    except ImportError:
        if not USER_AGENT:
            raise EnvironmentError(
                "SEC_USER_AGENT environment variable is required. "
                "Set it in your .env file: SEC_USER_AGENT='Your Name your@email.com'"
            )
        return USER_AGENT

# Function to get OPEN ROUTER API key
def get_openrouter_api_key():
    """Get the OPEN ROUTER API key from environment variable"""
    # Import here to avoid circular imports
    try:
        from utils.api_keys import ensure_openrouter_api_key
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
        from utils.api_keys import get_current_model
        return get_current_model()
    except ImportError:
        model = os.getenv('OPENROUTER_MODEL')
        if not model:
            print("Warning: No model configured. Please run 'python run.py model -switch' to configure a model.")
        return model