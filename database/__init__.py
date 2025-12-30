# Database package initialization

# Re-export commonly used utility function for convenience
from database.crud import get_db_connection

__all__ = ["get_db_connection"]
