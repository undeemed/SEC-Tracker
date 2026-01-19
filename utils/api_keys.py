import os
from pathlib import Path

def check_api_keys():
    """Check if required API keys are set and prompt user if not"""
    # Check SEC user agent
    sec_user_agent = os.getenv('SEC_USER_AGENT')
    
    # Check OpenRouter API key
    openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
    
    # Prompt for missing keys
    updated = False
    env_file = Path('.env')
    
    if not sec_user_agent:
        print("SEC API requires a user agent string for access.")
        user_agent = input("Please enter your SEC user agent (e.g., 'Your Name your@email.com'): ").strip()
        if user_agent:
            save_api_key_to_env('SEC_USER_AGENT', user_agent)
            updated = True
    
    # Only prompt for OpenRouter API key if user might need it
    # We'll check this more specifically in the modules that use it
    
    return updated

def save_api_key_to_env(key, value):
    """Save API key to .env file"""
    env_file = Path('.env')
    
    # If .env doesn't exist, create it from .env.example
    if not env_file.exists():
        env_example = Path('.env.example')
        if env_example.exists():
            # Copy the example file
            with open(env_example, 'r') as src, open(env_file, 'w') as dst:
                dst.write(src.read())
        else:
            env_file.touch()
    
    # Read current content
    with open(env_file, 'r') as f:
        lines = f.readlines()
    
    # Check if key already exists
    key_found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}\n"
            key_found = True
            break
    
    # If key not found, add it
    if not key_found:
        lines.append(f"{key}={value}\n")
    
    # Write back to file
    with open(env_file, 'w') as f:
        f.writelines(lines)
    
    # Also set in current environment
    os.environ[key] = value
    
    print(f"Saved {key} to .env file")

def ensure_sec_user_agent():
    """
    Ensure SEC user agent is available.
    SEC requires a valid contact email for API access.
    
    Returns:
        str: Valid user agent string
        
    Note:
        Will prompt user interactively if not configured.
        No longer uses insecure defaults.
    """
    user_agent = os.getenv('SEC_USER_AGENT')
    if not user_agent:
        print("\n" + "="*60)
        print("SEC API requires a user agent with valid contact info.")
        print("="*60)
        print("\nThis is required by SEC EDGAR for API access.")
        print("Format: 'Your Name your@email.com'")
        print("="*60 + "\n")
        
        user_agent = input("Please enter your SEC user agent: ").strip()
        if user_agent:
            # Validate format (should contain @ for email)
            if '@' not in user_agent:
                print("\n⚠️  Warning: User agent should include an email address.")
                confirm = input("Save anyway? (y/N): ").strip().lower()
                if confirm != 'y':
                    print("Please provide a valid user agent with email.")
                    return ensure_sec_user_agent()  # Retry
            
            save_api_key_to_env('SEC_USER_AGENT', user_agent)
            return user_agent
        else:
            raise EnvironmentError(
                "SEC_USER_AGENT is required. Please configure it in your .env file."
            )
    return user_agent

def ensure_openrouter_api_key():
    """Ensure OpenRouter API key is available for analysis features"""
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        print("\n" + "="*60)
        print("OpenRouter API key is required for AI analysis features.")
        print("="*60)
        print("\nGet your FREE API key:")
        print("  1. Visit: https://openrouter.ai/keys")
        print("  2. Sign in with Google/GitHub")
        print("  3. Click 'Create Key'")
        print("  4. Copy the key (starts with 'sk-or-v1-')")
        print("\nNote: Free tier includes credits for testing!")
        print("="*60 + "\n")
        api_key = input("Please enter your OpenRouter API key (or press Enter to skip): ").strip()
        if api_key:
            save_api_key_to_env('OPENROUTER_API_KEY', api_key)
            return api_key
        else:
            print("Analysis features will be disabled without an API key.")
            return None
    return api_key

def ensure_model_configured():
    """Ensure a model is configured, prompt if not"""
    model = os.getenv('OPENROUTER_MODEL')
    if not model:
        print("\nNo AI model configured.")
        print("\nPopular OpenRouter models:")
        print("  1. deepseek/deepseek-chat-v3.1:free")
        print("  2. x-ai/grok-4-fast:free")
        print("  3. google/gemini-2.0-flash-exp:free")
        print("  4. openai/gpt-oss-20b:free")
        print("  5. z-ai/glm-4.5-air:free")
        print("\nSee more models at: https://openrouter.ai/models")
        
        choice = input("\nEnter number (1-5) or full model name (press Enter for #1): ").strip()
        
        # Map number choices to models
        model_map = {
            "1": "deepseek/deepseek-chat-v3.1:free",
            "2": "x-ai/grok-4-fast:free",
            "3": "google/gemini-2.0-flash-exp:free",
            "4": "openai/gpt-oss-20b:free",
            "5": "z-ai/glm-4.5-air:free"
        }
        
        if not choice:
            model = "deepseek/deepseek-chat-v3.1:free"
        elif choice in model_map:
            model = model_map[choice]
        else:
            model = choice
            
        set_model(model)
    return model

def get_current_model():
    """Get the currently configured model"""
    model = os.getenv('OPENROUTER_MODEL')
    if not model:
        # Prompt user to configure model
        model = ensure_model_configured()
    return model

def get_slot_model(slot_number):
    """Get model from a specific slot"""
    key = f'OPENROUTER_MODEL_SLOT_{slot_number}'
    return os.getenv(key)

def list_model_slots():
    """List all configured model slots"""
    slots = []
    for i in range(1, 10):  # Check slots 1-9
        model = get_slot_model(i)
        if model:
            slots.append((i, model))
    
    if slots:
        print("\nConfigured Model Slots:")
        for slot_num, model in slots:
            current_indicator = " (current)" if model == get_current_model() else ""
            print(f"  Slot {slot_num}: {model}{current_indicator}")
    else:
        print("\nNo model slots configured.")
    
    return slots

def set_model(model_name, slot=None):
    """Set the OpenRouter model to use for analysis"""
    if slot:
        key = f'OPENROUTER_MODEL_SLOT_{slot}'
        save_api_key_to_env(key, model_name)
        print(f"Model set in slot {slot} to: {model_name}")
        # Also update the current model
        save_api_key_to_env('OPENROUTER_MODEL', model_name)
    else:
        save_api_key_to_env('OPENROUTER_MODEL', model_name)
        print(f"Model set to: {model_name}")
    
def switch_model(custom_slot=None):
    """Interactive model switching with slot support"""
    current_model = get_current_model()
    print(f"\nCurrent model: {current_model}")
    print("\nPopular OpenRouter models:")
    print("  1. deepseek/deepseek-chat-v3.1:free")
    print("  2. x-ai/grok-4-fast:free")
    print("  3. google/gemini-2.0-flash-exp:free")
    print("  4. openai/gpt-oss-20b:free")
    print("  5. z-ai/glm-4.5-air:free")
    print("  6. Enter custom model")
    print("\nSee more models at: https://openrouter.ai/models")
    
    if custom_slot:
        print(f"\nSlot: {custom_slot}")
        choice = input("\nEnter number (1-6) or full model name (press Enter to keep current): ").strip()
    else:
        choice = input("\nEnter number (1-6) or full model name (press Enter to keep current): ").strip()
    
    if choice:
        # Map number choices to models
        model_map = {
            "1": "deepseek/deepseek-chat-v3.1:free",
            "2": "x-ai/grok-4-fast:free",
            "3": "google/gemini-2.0-flash-exp:free",
            "4": "openai/gpt-oss-20b:free",
            "5": "z-ai/glm-4.5-air:free",
            "6": None  # Custom input
        }
        
        if choice == "6":
            new_model = input("Enter the full model name (e.g., 'openai/gpt-4o-mini:free'): ").strip()
            if not new_model:
                print("Custom model name cannot be empty.")
                return switch_model(custom_slot)
        elif choice in model_map:
            new_model = model_map[choice]
        else:
            new_model = choice
            
        set_model(new_model, custom_slot)
    else:
        print(f"Keeping current model: {current_model}")