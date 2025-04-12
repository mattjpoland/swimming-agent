import re
from datetime import datetime, timedelta

def validate_and_resolve_date(date_str, user_input):
    """
    Validates and resolves a date string, with fallback to relative date references.
    """
    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    
    # First try to parse the date from GPT
    try:
        parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
        
        # Validate date is plausible (not too far in past/future and matches relative terms)
        if "tomorrow" in user_input.lower() and abs((parsed_date - tomorrow).days) > 2:
            # If user asked for tomorrow but model returned something else
            return tomorrow.strftime("%Y-%m-%d")
        elif "today" in user_input.lower() and abs((parsed_date - today).days) > 2:
            # If user asked for today but model returned something else
            return today.strftime("%Y-%m-%d")
        elif abs((parsed_date - today).days) > 365:
            # If date is more than a year away, it's probably wrong
            if "tomorrow" in user_input.lower():
                return tomorrow.strftime("%Y-%m-%d")
            else:
                return today.strftime("%Y-%m-%d")
        else:
            # Date seems plausible
            return date_str
    except ValueError:
        # Invalid date format, extract from user input
        pass
    
    # If we get here, either the date was invalid or implausible
    # Use regex to find dates in user input
    date_matches = re.findall(r'\d{4}-\d{2}-\d{2}', user_input)
    if date_matches:
        return date_matches[0]
    
    # Process common time references
    if "tomorrow" in user_input.lower():
        return tomorrow.strftime("%Y-%m-%d")
    elif "today" in user_input.lower():
        return today.strftime("%Y-%m-%d")
    elif "next week" in user_input.lower():
        return (today + timedelta(days=7)).strftime("%Y-%m-%d")
    elif "weekend" in user_input.lower():
        # Find next Saturday
        days_until_saturday = (5 - today.weekday()) % 7
        if days_until_saturday == 0:  # If today is Saturday
            return today.strftime("%Y-%m-%d")
        return (today + timedelta(days=days_until_saturday)).strftime("%Y-%m-%d")
    
    # Default to today if no clear date reference
    return today.strftime("%Y-%m-%d")

def get_current_dates():
    """Returns current date and tomorrow's date as strings."""
    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    return today.strftime("%Y-%m-%d"), tomorrow.strftime("%Y-%m-%d")