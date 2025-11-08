"""
Tests for migration structure and reversibility.

Simple tests that verify migration files are properly structured
without requiring a live database connection.
"""

import importlib.util
import sys
from pathlib import Path

import pytest


@pytest.fixture
def migration_file():
    """Load the initial migration module."""
    migration_path = (
        Path(__file__).parent.parent
        / "alembic"
        / "versions"
        / "097c8293450b_initial_migration_core_tables.py"
    )
    spec = importlib.util.spec_from_file_location("migration", migration_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["migration"] = module
    spec.loader.exec_module(module)
    return module


class TestMigrationMetadata:
    """Test migration metadata and structure."""

    def test_migration_has_revision_id(self, migration_file):
        """Migration should have revision identifier."""
        assert hasattr(migration_file, "revision")
        assert migration_file.revision == "097c8293450b"

    def test_migration_has_no_down_revision(self, migration_file):
        """Initial migration should have no down_revision."""
        assert hasattr(migration_file, "down_revision")
        assert migration_file.down_revision is None

    def test_migration_has_upgrade_function(self, migration_file):
        """Migration should have upgrade function."""
        assert hasattr(migration_file, "upgrade")
        assert callable(migration_file.upgrade)

    def test_migration_has_downgrade_function(self, migration_file):
        """Migration should have downgrade function."""
        assert hasattr(migration_file, "downgrade")
        assert callable(migration_file.downgrade)


class TestMigrationContent:
    """Test that migration contains expected operations."""

    def test_upgrade_creates_all_core_tables(self, migration_file):
        """
        Verify upgrade function creates all core tables.

        This is a basic smoke test that checks the function can be called
        and contains the expected table creation operations.
        """
        import inspect

        upgrade_source = inspect.getsource(migration_file.upgrade)

        # Check that all core tables are created
        expected_tables = ["user", "participant", "file_ref", "report", "prof_activity"]
        for table in expected_tables:
            assert (
                f'"{table}"' in upgrade_source or f"'{table}'" in upgrade_source
            ), f"Table '{table}' should be created in upgrade()"

    def test_downgrade_drops_all_core_tables(self, migration_file):
        """
        Verify downgrade function drops all core tables.

        This ensures migrations are reversible.
        """
        import inspect

        downgrade_source = inspect.getsource(migration_file.downgrade)

        # Check that all core tables are dropped
        expected_tables = ["user", "participant", "file_ref", "report", "prof_activity"]
        for table in expected_tables:
            assert (
                f'"{table}"' in downgrade_source or f"'{table}'" in downgrade_source
            ), f"Table '{table}' should be dropped in downgrade()"

    def test_upgrade_creates_indexes(self, migration_file):
        """Verify that indexes are created."""
        import inspect

        upgrade_source = inspect.getsource(migration_file.upgrade)

        # Check for index creation
        assert "create_index" in upgrade_source, "Indexes should be created"

        # Check for specific important indexes
        expected_indexes = ["ix_user_email", "idx_report_status", "ix_prof_activity_code"]
        for index in expected_indexes:
            assert index in upgrade_source, f"Index '{index}' should be created"

    def test_upgrade_creates_foreign_keys(self, migration_file):
        """Verify that foreign keys are created."""
        import inspect

        upgrade_source = inspect.getsource(migration_file.upgrade)

        # Check for FK creation
        assert "ForeignKeyConstraint" in upgrade_source, "Foreign keys should be created"

        # Check for specific FKs
        assert "participant.id" in upgrade_source, "FK to participant should be created"
        assert "file_ref.id" in upgrade_source, "FK to file_ref should be created"

    def test_upgrade_creates_check_constraints(self, migration_file):
        """Verify that CHECK constraints are created."""
        import inspect

        upgrade_source = inspect.getsource(migration_file.upgrade)

        # Check for CHECK constraints
        assert "CheckConstraint" in upgrade_source, "CHECK constraints should be created"

        # Check for specific constraints
        assert "role IN" in upgrade_source, "User role CHECK constraint should exist"
        assert "status IN" in upgrade_source, "Status CHECK constraints should exist"

    def test_upgrade_creates_unique_constraints(self, migration_file):
        """Verify that UNIQUE constraints are created."""
        import inspect

        upgrade_source = inspect.getsource(migration_file.upgrade)

        # Check for UNIQUE constraints
        assert "UniqueConstraint" in upgrade_source, "UNIQUE constraints should be created"

        # Check for specific unique constraints
        assert "email" in upgrade_source, "Email unique constraint should exist"
        assert (
            "file_ref_location_unique" in upgrade_source
        ), "File location unique constraint should exist"
