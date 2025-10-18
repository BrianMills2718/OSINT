#!/usr/bin/env python3
"""
Database registry for managing all database integrations.

This module provides a central registry where database integrations are
registered and can be queried by ID, category, or availability.
"""

from typing import Dict, List, Optional
from database_integration_base import DatabaseIntegration, DatabaseCategory


class DatabaseRegistry:
    """
    Central registry for all database integrations.

    This singleton-style registry manages all available database integrations,
    allowing them to be queried, filtered, and accessed consistently throughout
    the application.

    Usage:
        # Register databases
        registry.register(ClearanceJobsIntegration())
        registry.register(DVIDSIntegration())

        # Get specific database
        cj = registry.get("clearancejobs")

        # Get all available databases (with API keys)
        available = registry.list_available({"dvids": "key-123"})

        # Get databases by category
        job_dbs = registry.get_by_category(DatabaseCategory.JOBS)
    """

    def __init__(self):
        """Initialize an empty registry."""
        self._databases: Dict[str, DatabaseIntegration] = {}
        self._categories: Dict[DatabaseCategory, List[str]] = {
            category: [] for category in DatabaseCategory
        }

    def register(self, database: DatabaseIntegration) -> None:
        """
        Register a new database integration.

        Args:
            database: The DatabaseIntegration instance to register

        Raises:
            ValueError: If a database with the same ID is already registered

        Example:
            registry.register(ClearanceJobsIntegration())
        """
        db_id = database.metadata.id

        if db_id in self._databases:
            raise ValueError(
                f"Database '{db_id}' is already registered. "
                f"Each database must have a unique ID."
            )

        self._databases[db_id] = database
        self._categories[database.metadata.category].append(db_id)

        print(f"✓ Registered database: {database.metadata.name} ({db_id})")

    def unregister(self, db_id: str) -> bool:
        """
        Unregister a database integration.

        Args:
            db_id: The database ID to unregister

        Returns:
            True if database was unregistered, False if not found

        Example:
            registry.unregister("clearancejobs")
        """
        if db_id not in self._databases:
            return False

        database = self._databases[db_id]
        category = database.metadata.category

        del self._databases[db_id]
        self._categories[category].remove(db_id)

        print(f"✓ Unregistered database: {database.metadata.name} ({db_id})")
        return True

    def get(self, db_id: str) -> Optional[DatabaseIntegration]:
        """
        Get a specific database by ID.

        Args:
            db_id: The database ID

        Returns:
            DatabaseIntegration instance, or None if not found

        Example:
            cj = registry.get("clearancejobs")
            if cj:
                results = await cj.execute_search(...)
        """
        return self._databases.get(db_id)

    def get_all(self) -> List[DatabaseIntegration]:
        """
        Get all registered databases.

        Returns:
            List of all DatabaseIntegration instances

        Example:
            for db in registry.get_all():
                print(db.metadata.name)
        """
        return list(self._databases.values())

    def get_by_category(self, category: DatabaseCategory) -> List[DatabaseIntegration]:
        """
        Get all databases in a specific category.

        Args:
            category: The DatabaseCategory to filter by

        Returns:
            List of DatabaseIntegration instances in that category

        Example:
            job_databases = registry.get_by_category(DatabaseCategory.JOBS)
            for db in job_databases:
                # Query all job databases
                results = await db.execute_search(...)
        """
        db_ids = self._categories.get(category, [])
        return [self._databases[db_id] for db_id in db_ids]

    def list_available(self, api_keys: Dict[str, str]) -> List[DatabaseIntegration]:
        """
        List databases that have required API keys or don't need them.

        This is useful to filter out databases that can't be queried due to
        missing API keys.

        Args:
            api_keys: Dict mapping database IDs to API keys
                     Example: {"dvids": "key-123", "sam": "SAM-456"}

        Returns:
            List of DatabaseIntegration instances that can be queried

        Example:
            api_keys = {
                "dvids": os.getenv("DVIDS_API_KEY"),
                "sam": os.getenv("SAM_GOV_API_KEY")
            }
            available = registry.list_available(api_keys)
            # Query only databases we have keys for
        """
        available = []

        for db in self._databases.values():
            # If no API key required, always available
            if not db.metadata.requires_api_key:
                available.append(db)
            # If API key required, check if we have it
            elif db.metadata.id in api_keys and api_keys[db.metadata.id]:
                available.append(db)

        return available

    def get_stats(self) -> Dict:
        """
        Get statistics about registered databases.

        Returns:
            Dict with statistics

        Example:
            stats = registry.get_stats()
            print(f"Total databases: {stats['total']}")
            print(f"By category: {stats['by_category']}")
        """
        stats = {
            "total": len(self._databases),
            "by_category": {
                category.value: len(db_ids)
                for category, db_ids in self._categories.items()
            },
            "requires_api_key": sum(
                1 for db in self._databases.values()
                if db.metadata.requires_api_key
            ),
            "databases": {
                db_id: {
                    "name": db.metadata.name,
                    "category": db.metadata.category.value,
                    "requires_api_key": db.metadata.requires_api_key
                }
                for db_id, db in self._databases.items()
            }
        }

        return stats

    def __len__(self) -> int:
        """Return number of registered databases."""
        return len(self._databases)

    def __contains__(self, db_id: str) -> bool:
        """Check if a database is registered."""
        return db_id in self._databases

    def __repr__(self) -> str:
        """String representation of registry."""
        return f"DatabaseRegistry({len(self._databases)} databases)"


# Global registry instance
# Import this in other modules: from database_registry import registry
registry = DatabaseRegistry()
