"""
SQLite storage layer for Workshop - Compatibility shim.

This module maintains backward compatibility by re-exporting the new
modular storage implementation. All code has been migrated to the
storage/ package.

For new code, import directly from storage/:
    from .storage import WorkshopStorage
"""
from .storage import WorkshopStorage as WorkshopStorageSQLite

# Re-export for backward compatibility
__all__ = ['WorkshopStorageSQLite']
