import pygit2
from typing import Callable, Any

def get_callbacks(token: str | None = None) -> pygit2.RemoteCallbacks | None:
    if not token:
        return None
        
    callbacks = pygit2.RemoteCallbacks()
    
    # Credentials callback
    def credentials_cb(url: str, username_from_url: str | None, allowed_types: int) -> pygit2.UserPass:
        return pygit2.UserPass(token, "x-oauth-basic")
        
    callbacks.credentials = credentials_cb
    return callbacks
