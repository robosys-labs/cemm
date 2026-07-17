"""One-way, fail-closed migration helpers into the v3.4.7 substrate."""
from .v347 import LegacyMigrationError, migrate_legacy_fact, migrate_legacy_referent
__all__ = ["LegacyMigrationError", "migrate_legacy_fact", "migrate_legacy_referent"]
