"""
User settings and utilities
"""

def generate_bot_name(full_name: str) -> str:
    """
    Generate a bot name based on user's full name
    """
    if not full_name:
        return "Digital Twin Bot"
    
    # Simple logic: use first name + "'s Assistant"
    first_name = full_name.split()[0] if full_name.split() else full_name
    return f"{first_name}'s Bot"