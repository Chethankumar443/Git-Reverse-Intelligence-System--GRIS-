"""
Git Reverse — Error Taxonomy Classifier
"""

def classify_error(msg: str) -> dict:
    msg_l = msg.lower()
    if "invalid github url" in msg_l or "invalid input" in msg_l:
        return {"category": "Invalid input", "can_retry": False}
    elif "401" in msg_l or "unauthorized" in msg_l or "invalid api key" in msg_l:
        return {"category": "Authentication failed", "can_retry": True}
    elif "rate limit" in msg_l or "429" in msg_l:
        return {"category": "Rate limited", "can_retry": True}
    elif "not found" in msg_l or "404" in msg_l:
        return {"category": "Resource not found", "can_retry": False}
    elif "connection refused" in msg_l or "network" in msg_l or "unreachable" in msg_l:
        return {"category": "Network unreachable", "can_retry": True}
    else:
        return {"category": "Internal error", "can_retry": True}
