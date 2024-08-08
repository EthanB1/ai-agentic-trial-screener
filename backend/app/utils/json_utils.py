import json

def sanitize_for_json(data):
    """
    Sanitize the input data to ensure it can be properly encoded as JSON.
    """
    if isinstance(data, dict):
        return {sanitize_for_json(key): sanitize_for_json(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [sanitize_for_json(item) for item in data]
    elif isinstance(data, str):
        # Replace any non-UTF-8 characters with a placeholder
        return data.encode('utf-8', errors='replace').decode('utf-8')
    else:
        return data