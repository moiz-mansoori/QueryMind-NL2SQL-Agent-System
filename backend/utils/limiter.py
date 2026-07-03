from slowapi import Limiter
from slowapi.util import get_remote_address
from config import TESTING

# Global limiter instance (disabled during testing)
limiter = Limiter(key_func=get_remote_address, enabled=not TESTING)

