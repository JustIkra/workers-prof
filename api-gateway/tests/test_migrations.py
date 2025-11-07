"""
Tests for Alembic migrations against PostgreSQL.

Ensures migrations apply cleanly on a real PostgreSQL database,
can be rolled back, and enforce key constraints.
"""

import os
import uuid

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
from sqlalchemy.orm import sessionmaker

# ===== Test Configuration =====


@pytest.fixture(scope="module")
def engine():
    """
    Create a temporary PostgreSQL database for migration tests.

    Uses POSTGRES_DSN to connect to the server, creates an isolated
    database for the duration of the test module, and drops it afterwards.
    """
    raw_dsn = os.getenv("POSTGRES_DSN")
    if not raw_dsn:
        pytest.skip("POSTGRES_DSN is required to run migration tests against PostgreSQL")

    base_url = make_url(raw_dsn)
    if base_url.get_backend_name() != "postgresql":
        pytest.skip("Migration tests require a PostgreSQL DSN")

    if not base_url.database:
        pytest.skip("POSTGRES_DSN must include a database name")

    try:
        __import__("psycopg")
    except ModuleNotFoundError as exc:  # pragma: no cover - defensive guard
        pytest.skip(f"psycopg driver is required for migration tests: {exc}")

    base_db = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in base_url.database.lower())
    test_db_name = f"{base_db}_migrations_{uuid.uuid4().hex}"

    admin_url = base_url.set(drivername="postgresql+psycopg", database="postgres")
    admin_engine = create_engine(
        admin_url.render_as_string(hide_password=False),
        isolation_level="AUTOCOMMIT",
    )

    try:
        try:
            with admin_engine.connect() as conn:
                conn.execute(text(f'DROP DATABASE IF EXISTS "{test_db_name}"'))
                conn.execute(text(f'CREATE DATABASE "{test_db_name}"'))
        except ProgrammingError as exc:
            if "permission denied to create database" in str(exc):
                pytest.skip(
                    "PostgreSQL role lacks CREATE DATABASE privilege. "
                    "Run migration tests with a superuser or pre-created test database."
                )
            raise
    except OperationalError as exc:
        pytest.skip(f"PostgreSQL server is not available for migration tests: {exc}")
    finally:
        admin_engine.dispose()

    test_url = base_url.set(drivername="postgresql+psycopg", database=test_db_name)
    engine = create_engine(test_url.render_as_string(hide_password=False))

    try:
        yield engine
    finally:
        engine.dispose()

        admin_engine = create_engine(
            admin_url.render_as_string(hide_password=False),
            isolation_level="AUTOCOMMIT",
        )
        try:
            with admin_engine.connect() as conn:
                try:
                    conn.execute(text(f'DROP DATABASE IF EXISTS "{test_db_name}" WITH (FORCE)'))
                except OperationalError:
                    # Fallback for older PostgreSQL versions without WITH (FORCE)
                    conn.execute(
                        text(
                            """
                            SELECT pg_terminate_backend(pid)
                            FROM pg_stat_activity
                            WHERE datname = :db_name
                              AND pid <> pg_backend_pid()
                            """
                        ),
                        {"db_name": test_db_name},
                    )
                    conn.execute(text(f'DROP DATABASE IF EXISTS "{test_db_name}"'))
        finally:
            admin_engine.dispose()


@pytest.fixture(scope="module")
def session_factory(engine):
    """Create session factory for tests."""
    return sessionmaker(bind=engine)


@pytest.fixture
def db_session(session_factory):
    """Provide a database session for each test."""
    session = session_factory()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="module", autouse=True)
def apply_migrations(engine):
    """
    Apply migrations before running tests.

    This runs alembic upgrade head to create all tables.
    After tests complete, runs downgrade to clean up.
    """
    from alembic import command
    from alembic.config import Config

    # Create Alembic config
    alembic_cfg = Config("alembic.ini")
    # Override database URL to use test engine
    url_value = engine.url.render_as_string(hide_password=False).replace("%", "%%")
    alembic_cfg.set_main_option("sqlalchemy.url", url_value)
    # Run upgrade

    command.upgrade(alembic_cfg, "head")

    yield

    # Run downgrade to clean up
    command.downgrade(alembic_cfg, "base")


# ===== Migration Tests =====


class TestMigrationStructure:
    """Test that migrations create correct table structure."""

    def test_all_tables_created(self, engine):
        """All core tables should be created after migration."""
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        expected_tables = {
            "user",
            "participant",
            "file_ref",
            "report",
            "prof_activity",
            "weight_table",
        }
        assert expected_tables.issubset(set(tables)), (
            f"Missing tables: {expected_tables - set(tables)}"
        )

    def test_user_table_structure(self, engine):
        """User table should have correct columns and constraints."""
        inspector = inspect(engine)
        columns = {col["name"]: col for col in inspector.get_columns("user")}

        # Check required columns exist
        assert "id" in columns
        assert "email" in columns
        assert "password_hash" in columns
        assert "role" in columns
        assert "status" in columns
        assert "created_at" in columns
        assert "approved_at" in columns

        # Check unique constraint on email
        unique_constraints = inspector.get_unique_constraints("user")
        email_unique = any("email" in uc.get("column_names", []) for uc in unique_constraints)
        assert email_unique, "Email should have unique constraint"

    def test_participant_table_structure(self, engine):
        """Participant table should have correct columns."""
        inspector = inspect(engine)
        columns = {col["name"]: col for col in inspector.get_columns("participant")}

        assert "id" in columns
        assert "full_name" in columns
        assert "birth_date" in columns
        assert "external_id" in columns
        assert "created_at" in columns

    def test_report_table_foreign_keys(self, engine):
        """Report table should have foreign keys to participant and file_ref."""
        inspector = inspect(engine)
        foreign_keys = inspector.get_foreign_keys("report")

        # Should have FK to participant
        participant_fk = any(fk["referred_table"] == "participant" for fk in foreign_keys)
        assert participant_fk, "Report should have FK to participant"

        # Should have FK to file_ref
        file_ref_fk = any(fk["referred_table"] == "file_ref" for fk in foreign_keys)
        assert file_ref_fk, "Report should have FK to file_ref"

    def test_indexes_created(self, engine):
        """Important indexes should be created."""
        inspector = inspect(engine)

        # Check user email index
        user_indexes = inspector.get_indexes("user")
        assert any("email" in idx.get("column_names", []) for idx in user_indexes)

        # Check participant indexes
        participant_indexes = inspector.get_indexes("participant")
        assert any("full_name" in idx.get("column_names", []) for idx in participant_indexes)

        # Check report indexes
        report_indexes = inspector.get_indexes("report")
        assert any("status" in idx.get("column_names", []) for idx in report_indexes)

        # Check weight table indexes exist
        weight_indexes = inspector.get_indexes("weight_table")
        assert any("prof_activity_id" in idx.get("column_names", []) for idx in weight_indexes)


class TestConstraintEnforcement:
    """Test that database constraints are properly enforced."""

    def test_user_email_unique__duplicate__raises_error(self, db_session):
        """Duplicate email should violate unique constraint."""
        # Insert first user
        db_session.execute(
            text(
                """
                INSERT INTO "user" (id, email, password_hash, role, status)
                VALUES (:id, :email, :password_hash, :role, :status)
            """
            ),
            {
                "id": str(uuid.uuid4()),
                "email": "test@example.com",
                "password_hash": "hashed_password",
                "role": "USER",
                "status": "ACTIVE",
            },
        )
        db_session.commit()

        # Try to insert duplicate email
        with pytest.raises(IntegrityError):
            db_session.execute(
                text(
                    """
                    INSERT INTO "user" (id, email, password_hash, role, status)
                    VALUES (:id, :email, :password_hash, :role, :status)
                """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "email": "test@example.com",  # Duplicate
                    "password_hash": "another_hash",
                    "role": "ADMIN",
                    "status": "PENDING",
                },
            )
            db_session.commit()

    def test_file_ref_unique_location__duplicate__raises_error(self, db_session):
        """Duplicate (storage, bucket, key) should violate unique constraint."""
        # Insert first file_ref
        db_session.execute(
            text(
                """
                INSERT INTO file_ref (id, storage, bucket, key, mime, size_bytes)
                VALUES (:id, :storage, :bucket, :key, :mime, :size_bytes)
            """
            ),
            {
                "id": str(uuid.uuid4()),
                "storage": "LOCAL",
                "bucket": "reports",
                "key": "test/file.docx",
                "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "size_bytes": 12345,
            },
        )
        db_session.commit()

        # Try to insert duplicate location
        with pytest.raises(IntegrityError):
            db_session.execute(
                text(
                    """
                    INSERT INTO file_ref (id, storage, bucket, key, mime, size_bytes)
                    VALUES (:id, :storage, :bucket, :key, :mime, :size_bytes)
                """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "storage": "LOCAL",  # Same storage
                    "bucket": "reports",  # Same bucket
                    "key": "test/file.docx",  # Same key
                    "mime": "application/pdf",
                    "size_bytes": 99999,
                },
            )
            db_session.commit()

    def test_report_participant_type_unique__duplicate__raises_error(self, db_session):
        """Duplicate (participant_id, type) should violate unique constraint."""
        # Create participant and file_ref first
        participant_id = str(uuid.uuid4())
        file_ref_id = str(uuid.uuid4())

        db_session.execute(
            text("INSERT INTO participant (id, full_name) VALUES (:id, :full_name)"),
            {"id": participant_id, "full_name": "Test Participant"},
        )
        db_session.execute(
            text(
                "INSERT INTO file_ref (id, storage, bucket, key, mime, size_bytes) "
                "VALUES (:id, :storage, :bucket, :key, :mime, :size_bytes)"
            ),
            {
                "id": file_ref_id,
                "storage": "LOCAL",
                "bucket": "reports",
                "key": "unique_key.docx",
                "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "size_bytes": 1000,
            },
        )
        db_session.commit()

        # Insert first report
        db_session.execute(
            text(
                """
                INSERT INTO report (id, participant_id, type, status, file_ref_id)
                VALUES (:id, :participant_id, :type, :status, :file_ref_id)
            """
            ),
            {
                "id": str(uuid.uuid4()),
                "participant_id": participant_id,
                "type": "REPORT_1",
                "status": "UPLOADED",
                "file_ref_id": file_ref_id,
            },
        )
        db_session.commit()

        # Try to insert duplicate (participant_id, type)
        with pytest.raises(IntegrityError):
            file_ref_id_2 = str(uuid.uuid4())
            db_session.execute(
                text(
                    "INSERT INTO file_ref (id, storage, bucket, key, mime, size_bytes) "
                    "VALUES (:id, :storage, :bucket, :key, :mime, :size_bytes)"
                ),
                {
                    "id": file_ref_id_2,
                    "storage": "LOCAL",
                    "bucket": "reports",
                    "key": "another_unique_key.docx",
                    "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "size_bytes": 2000,
                },
            )
            db_session.execute(
                text(
                    """
                    INSERT INTO report (id, participant_id, type, status, file_ref_id)
                    VALUES (:id, :participant_id, :type, :status, :file_ref_id)
                """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "participant_id": participant_id,  # Same participant
                    "type": "REPORT_1",  # Same type
                    "status": "EXTRACTED",
                    "file_ref_id": file_ref_id_2,
                },
            )
            db_session.commit()

    def test_prof_activity_code_unique__duplicate__raises_error(self, db_session):
        """Duplicate prof_activity code should violate unique constraint."""
        # Insert first activity
        db_session.execute(
            text("INSERT INTO prof_activity (id, code, name) VALUES (:id, :code, :name)"),
            {"id": str(uuid.uuid4()), "code": "developer", "name": "Software Developer"},
        )
        db_session.commit()

        # Try to insert duplicate code
        with pytest.raises(IntegrityError):
            db_session.execute(
                text("INSERT INTO prof_activity (id, code, name) VALUES (:id, :code, :name)"),
                {"id": str(uuid.uuid4()), "code": "developer", "name": "Senior Developer"},
            )
            db_session.commit()

    def test_weight_table_version_unique__duplicate__raises_error(self, db_session):
        """Duplicate version per professional activity should violate unique constraint."""
        prof_activity_id = str(uuid.uuid4())

        # Ensure professional activity exists
        db_session.execute(
            text("INSERT INTO prof_activity (id, code, name) VALUES (:id, :code, :name)"),
            {"id": prof_activity_id, "code": "wt_admin", "name": "Weight Admin"},
        )
        db_session.commit()

        payload = '[{"metric_code": "m1", "weight": "0.5"}, {"metric_code": "m2", "weight": "0.5"}]'

        db_session.execute(
            text(
                """
                INSERT INTO weight_table (id, prof_activity_id, version, weights, is_active)
                VALUES (:id, :prof_activity_id, :version, :weights, :is_active)
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "prof_activity_id": prof_activity_id,
                "version": 1,
                "weights": payload,
                "is_active": False,
            },
        )
        db_session.commit()

        with pytest.raises(IntegrityError):
            db_session.execute(
                text(
                    """
                    INSERT INTO weight_table (id, prof_activity_id, version, weights, is_active)
                    VALUES (:id, :prof_activity_id, :version, :weights, :is_active)
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "prof_activity_id": prof_activity_id,
                    "version": 1,
                    "weights": payload,
                    "is_active": False,
                },
            )
            db_session.commit()

    def test_weight_table_active_unique__conflict__raises_error(self, db_session):
        """Marking second version as active should violate partial unique constraint."""
        prof_activity_id = str(uuid.uuid4())

        db_session.execute(
            text("INSERT INTO prof_activity (id, code, name) VALUES (:id, :code, :name)"),
            {"id": prof_activity_id, "code": "wt_active", "name": "Weight Active"},
        )

        payload = '[{"metric_code": "m1", "weight": "1.0"}]'

        first_id = str(uuid.uuid4())
        second_id = str(uuid.uuid4())

        db_session.execute(
            text(
                """
                INSERT INTO weight_table (id, prof_activity_id, version, weights, is_active)
                VALUES (:id, :prof_activity_id, :version, :weights, :is_active)
                """
            ),
            {
                "id": first_id,
                "prof_activity_id": prof_activity_id,
                "version": 1,
                "weights": payload,
                "is_active": True,
            },
        )
        db_session.execute(
            text(
                """
                INSERT INTO weight_table (id, prof_activity_id, version, weights, is_active)
                VALUES (:id, :prof_activity_id, :version, :weights, :is_active)
                """
            ),
            {
                "id": second_id,
                "prof_activity_id": prof_activity_id,
                "version": 2,
                "weights": payload,
                "is_active": False,
            },
        )
        db_session.commit()

        with pytest.raises(IntegrityError):
            db_session.execute(
                text("UPDATE weight_table SET is_active = :is_active WHERE id = :id"),
                {
                    "id": second_id,
                    "is_active": True,
                },
            )
            db_session.commit()


class TestForeignKeyConstraints:
    """Test foreign key constraints and cascades."""

    def test_report_participant_fk__delete_cascade__deletes_reports(self, db_session):
        """Deleting participant should cascade delete reports."""
        # Create participant, file_ref, and report
        participant_id = str(uuid.uuid4())
        file_ref_id = str(uuid.uuid4())
        report_id = str(uuid.uuid4())

        db_session.execute(
            text("INSERT INTO participant (id, full_name) VALUES (:id, :full_name)"),
            {"id": participant_id, "full_name": "Test Participant"},
        )
        db_session.execute(
            text(
                "INSERT INTO file_ref (id, storage, bucket, key, mime, size_bytes) "
                "VALUES (:id, :storage, :bucket, :key, :mime, :size_bytes)"
            ),
            {
                "id": file_ref_id,
                "storage": "LOCAL",
                "bucket": "reports",
                "key": "cascade_test.docx",
                "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "size_bytes": 5000,
            },
        )
        db_session.execute(
            text(
                "INSERT INTO report (id, participant_id, type, status, file_ref_id) "
                "VALUES (:id, :participant_id, :type, :status, :file_ref_id)"
            ),
            {
                "id": report_id,
                "participant_id": participant_id,
                "type": "REPORT_1",
                "status": "UPLOADED",
                "file_ref_id": file_ref_id,
            },
        )
        db_session.commit()

        # Delete participant
        db_session.execute(text("DELETE FROM participant WHERE id = :id"), {"id": participant_id})
        db_session.commit()

        # Report should be deleted (cascade)
        result = db_session.execute(
            text("SELECT COUNT(*) FROM report WHERE id = :id"), {"id": report_id}
        )
        count = result.scalar()
        assert count == 0, "Report should be deleted when participant is deleted (CASCADE)"
