# Simple alert storage (in-memory)
_alerts = []

def add_alert(message):
    """Add a new alert message to the in-memory storage."""
    _alerts.append({"message": message})

def get_alerts():
    """Retrieve all stored alert messages."""
    return _alerts
