import pytest
import sqlite3
import tempfile
import os
from datetime import datetime, timezone
from unittest.mock import patch

from heatpump_stats.adapters.sqlite import SqliteAdapter
from heatpump_stats.domain.configuration import (
    HeatPumpConfig,
    CircuitConfig,
    DHWConfig,
    WeeklySchedule,
    TimeSlot,
)


class TestSqliteAdapter:
    """Test suite for the SqliteAdapter class."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database file path."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        # Cleanup
        try:
            os.unlink(path)
        except Exception:
            pass

    @pytest.fixture
    def mock_settings(self, temp_db_path):
        """Mock settings with temporary database path."""
        with patch("heatpump_stats.adapters.sqlite.settings") as mock:
            mock.SQLITE_DB_PATH = temp_db_path
            yield mock

    @pytest.fixture
    def adapter(self, temp_db_path):
        """Create a SqliteAdapter instance with temporary database."""
        return SqliteAdapter(db_path=temp_db_path)

    @pytest.fixture
    def sample_config(self):
        """Create a sample HeatPumpConfig."""
        return HeatPumpConfig(
            circuits=[
                CircuitConfig(
                    circuit_id=0,
                    name="Living Room",
                    temp_comfort=22.0,
                    temp_normal=20.0,
                    temp_reduced=18.0,
                ),
                CircuitConfig(
                    circuit_id=1,
                    name="Bedroom",
                    temp_comfort=20.0,
                    temp_normal=19.0,
                    temp_reduced=17.0,
                ),
            ],
            dhw=DHWConfig(active=True, temp_target=50.0),
        )

    @pytest.fixture
    def complex_config(self):
        """Create a complex HeatPumpConfig with schedules."""
        schedule = WeeklySchedule(
            active=True,
            mon=[
                TimeSlot(start="06:00", end="08:00", mode="comfort", position=0),
                TimeSlot(start="17:00", end="22:00", mode="comfort", position=1),
            ],
            tue=[TimeSlot(start="06:00", end="08:00", mode="comfort", position=0)],
        )

        return HeatPumpConfig(
            circuits=[
                CircuitConfig(
                    circuit_id=0,
                    name="Main Circuit",
                    temp_comfort=22.0,
                    temp_normal=20.0,
                    temp_reduced=18.0,
                    schedule=schedule,
                )
            ],
            dhw=DHWConfig(active=True, temp_target=50.0, schedule=schedule),
        )

    def test_initialization(self, temp_db_path):
        """Test SqliteAdapter initialization."""
        adapter = SqliteAdapter(db_path=temp_db_path)

        assert adapter.db_path == temp_db_path
        assert os.path.exists(temp_db_path)

    def test_database_schema_creation(self, temp_db_path):
        """Test that database schema is created correctly."""
        SqliteAdapter(db_path=temp_db_path)

        # Verify table exists
        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='configs'")
            assert cursor.fetchone() is not None

    def test_database_schema_columns(self, temp_db_path):
        """Test that database table has correct columns."""
        SqliteAdapter(db_path=temp_db_path)

        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.execute("PRAGMA table_info(configs)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}

            assert "id" in columns
            assert "timestamp" in columns
            assert "config_json" in columns
            assert columns["timestamp"] == "TEXT"
            assert columns["config_json"] == "TEXT"

    def test_init_db_creates_directory(self, temp_db_path):
        """Test that initialization creates parent directories if needed."""
        # Create a path with non-existent parent directory
        parent_dir = os.path.join(os.path.dirname(temp_db_path), "test_subdir")
        db_path = os.path.join(parent_dir, "test.db")

        try:
            os.makedirs(parent_dir, exist_ok=True)
            SqliteAdapter(db_path=db_path)
            assert os.path.exists(db_path)
        finally:
            # Cleanup
            try:
                os.unlink(db_path)
                os.rmdir(parent_dir)
            except Exception:
                pass

    def test_init_db_error_handling(self):
        """Test initialization error handling with invalid path."""
        invalid_path = "/invalid/path/that/does/not/exist/test.db"

        with pytest.raises(Exception):
            SqliteAdapter(db_path=invalid_path)

    @pytest.mark.asyncio
    async def test_save_config_success(self, adapter, sample_config):
        """Test successful configuration save."""
        await adapter.save_config(sample_config)

        # Verify data was saved
        with sqlite3.connect(adapter.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM configs")
            count = cursor.fetchone()[0]
            assert count == 1

    @pytest.mark.asyncio
    async def test_save_config_data_integrity(self, adapter, sample_config):
        """Test that saved configuration data is intact."""
        await adapter.save_config(sample_config)

        with sqlite3.connect(adapter.db_path) as conn:
            cursor = conn.execute("SELECT config_json FROM configs")
            row = cursor.fetchone()

            # Verify JSON can be parsed back
            loaded_config = HeatPumpConfig.model_validate_json(row[0])
            assert loaded_config.circuits[0].name == "Living Room"
            assert loaded_config.circuits[1].name == "Bedroom"
            assert loaded_config.dhw is not None
            assert loaded_config.dhw.temp_target == 50.0

    @pytest.mark.asyncio
    async def test_save_config_timestamp(self, adapter, sample_config):
        """Test that timestamp is saved correctly."""
        before = datetime.now(timezone.utc)
        await adapter.save_config(sample_config)
        after = datetime.now(timezone.utc)

        with sqlite3.connect(adapter.db_path) as conn:
            cursor = conn.execute("SELECT timestamp FROM configs")
            row = cursor.fetchone()

            timestamp = datetime.fromisoformat(row[0])
            assert before <= timestamp <= after

    @pytest.mark.asyncio
    async def test_save_multiple_configs(self, adapter, sample_config):
        """Test saving multiple configurations."""
        await adapter.save_config(sample_config)

        # Modify config
        sample_config.circuits[0].temp_comfort = 23.0
        await adapter.save_config(sample_config)

        # Verify both saved
        with sqlite3.connect(adapter.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM configs")
            count = cursor.fetchone()[0]
            assert count == 2

    @pytest.mark.asyncio
    async def test_save_complex_config(self, adapter, complex_config):
        """Test saving complex configuration with schedules."""
        await adapter.save_config(complex_config)

        # Verify data was saved
        with sqlite3.connect(adapter.db_path) as conn:
            cursor = conn.execute("SELECT config_json FROM configs")
            row = cursor.fetchone()

            loaded_config = HeatPumpConfig.model_validate_json(row[0])
            assert loaded_config.circuits[0].schedule is not None
            assert loaded_config.circuits[0].schedule.active is True
            assert len(loaded_config.circuits[0].schedule.mon) == 2

    @pytest.mark.asyncio
    async def test_save_config_error_handling(self, adapter):
        """Test error handling when save fails."""
        # Close the database connection and remove file to cause error
        os.chmod(adapter.db_path, 0o444)  # Read-only

        try:
            with pytest.raises(Exception):
                await adapter.save_config(HeatPumpConfig())
        finally:
            os.chmod(adapter.db_path, 0o644)  # Restore permissions

    @pytest.mark.asyncio
    async def test_load_latest_config_success(self, adapter, sample_config):
        """Test successfully loading latest configuration."""
        await adapter.save_config(sample_config)

        loaded_config = await adapter.load_latest_config()

        assert loaded_config is not None
        assert len(loaded_config.circuits) == 2
        assert loaded_config.circuits[0].name == "Living Room"
        assert loaded_config.dhw is not None
        assert loaded_config.dhw.temp_target == 50.0

    @pytest.mark.asyncio
    async def test_load_latest_config_empty_database(self, adapter):
        """Test loading from empty database returns None."""
        loaded_config = await adapter.load_latest_config()

        assert loaded_config is None

    @pytest.mark.asyncio
    async def test_load_latest_config_returns_most_recent(self, adapter, sample_config):
        """Test that load_latest_config returns the most recent configuration."""
        # Save first config
        await adapter.save_config(sample_config)

        # Modify and save second config
        sample_config.circuits[0].temp_comfort = 25.0
        await adapter.save_config(sample_config)

        # Load latest
        loaded_config = await adapter.load_latest_config()

        assert loaded_config.circuits[0].temp_comfort == 25.0

    @pytest.mark.asyncio
    async def test_load_latest_config_complex(self, adapter, complex_config):
        """Test loading complex configuration with schedules."""
        await adapter.save_config(complex_config)

        loaded_config = await adapter.load_latest_config()

        assert loaded_config is not None
        assert loaded_config.circuits[0].schedule is not None
        assert len(loaded_config.circuits[0].schedule.mon) == 2
        assert loaded_config.circuits[0].schedule.mon[0].start == "06:00"

    @pytest.mark.asyncio
    async def test_load_latest_config_handles_invalid_json(self, adapter):
        """Test loading handles invalid JSON gracefully."""
        # Insert invalid JSON directly
        with sqlite3.connect(adapter.db_path) as conn:
            conn.execute(
                "INSERT INTO configs (timestamp, config_json) VALUES (?, ?)",
                (datetime.now(timezone.utc).isoformat(), "invalid json {{{"),
            )
            conn.commit()

        loaded_config = await adapter.load_latest_config()

        # Should return None when JSON is invalid
        assert loaded_config is None

    @pytest.mark.asyncio
    async def test_save_and_load_empty_config(self, adapter):
        """Test saving and loading an empty configuration."""
        empty_config = HeatPumpConfig()
        await adapter.save_config(empty_config)

        loaded_config = await adapter.load_latest_config()

        assert loaded_config is not None
        assert len(loaded_config.circuits) == 0
        assert loaded_config.dhw is None

    @pytest.mark.asyncio
    async def test_save_config_with_none_values(self, adapter):
        """Test saving configuration with None values."""
        config = HeatPumpConfig(
            circuits=[
                CircuitConfig(
                    circuit_id=0,
                    name=None,
                    temp_comfort=None,
                    temp_normal=None,
                    temp_reduced=None,
                )
            ]
        )
        await adapter.save_config(config)

        loaded_config = await adapter.load_latest_config()

        assert loaded_config is not None
        assert loaded_config.circuits[0].name is None
        assert loaded_config.circuits[0].temp_comfort is None

    @pytest.mark.asyncio
    async def test_concurrent_saves(self, adapter, sample_config):
        """Test concurrent save operations."""
        import asyncio

        # Create multiple configs with different values
        configs = []
        for i in range(5):
            config = HeatPumpConfig(circuits=[CircuitConfig(circuit_id=0, temp_comfort=20.0 + i)])
            configs.append(config)

        # Save concurrently
        await asyncio.gather(*[adapter.save_config(config) for config in configs])

        # Verify all were saved
        with sqlite3.connect(adapter.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM configs")
            count = cursor.fetchone()[0]
            assert count == 5

    @pytest.mark.asyncio
    async def test_save_config_preserves_order(self, adapter):
        """Test that multiple saves preserve insertion order."""
        configs = []
        for i in range(3):
            config = HeatPumpConfig(circuits=[CircuitConfig(circuit_id=0, temp_comfort=20.0 + i)])
            await adapter.save_config(config)
            configs.append(config)

        # Verify latest is the last one saved
        loaded_config = await adapter.load_latest_config()
        assert loaded_config.circuits[0].temp_comfort == 22.0

    def test_sync_save_method(self, adapter, sample_config):
        """Test the synchronous _save_config_sync method directly."""
        adapter._save_config_sync(sample_config)

        with sqlite3.connect(adapter.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM configs")
            count = cursor.fetchone()[0]
            assert count == 1

    def test_sync_load_method(self, adapter, sample_config):
        """Test the synchronous _load_latest_config_sync method directly."""
        adapter._save_config_sync(sample_config)

        loaded_config = adapter._load_latest_config_sync()

        assert loaded_config is not None
        assert loaded_config.circuits[0].name == "Living Room"

    def test_sync_load_method_empty(self, adapter):
        """Test sync load method with empty database."""
        loaded_config = adapter._load_latest_config_sync()
        assert loaded_config is None

    @pytest.mark.asyncio
    async def test_database_file_persistence(self, temp_db_path, sample_config):
        """Test that database file persists after adapter is destroyed."""
        adapter1 = SqliteAdapter(db_path=temp_db_path)
        await adapter1.save_config(sample_config)
        del adapter1

        # Create new adapter with same path
        adapter2 = SqliteAdapter(db_path=temp_db_path)
        loaded_config = await adapter2.load_latest_config()

        assert loaded_config is not None
        assert loaded_config.circuits[0].name == "Living Room"

    def test_default_db_path_from_settings(self):
        """Test that adapter can use custom path or default."""
        # Test with custom path
        custom_path = "/tmp/test_custom.db"
        try:
            adapter = SqliteAdapter(db_path=custom_path)
            assert adapter.db_path == custom_path
            assert os.path.exists(custom_path)
        finally:
            try:
                os.unlink(custom_path)
            except Exception:
                pass

        # Test that it uses some default path when not specified
        # (we can't easily test the exact default due to import-time binding)
        adapter = SqliteAdapter()
        assert adapter.db_path is not None
        assert isinstance(adapter.db_path, str)

    @pytest.mark.asyncio
    async def test_load_config_database_error(self, adapter):
        """Test load_config handles database errors gracefully."""
        # Close and delete the database
        os.unlink(adapter.db_path)

        # Should return None on error
        loaded_config = await adapter.load_latest_config()
        assert loaded_config is None

    @pytest.mark.asyncio
    async def test_save_load_roundtrip(self, adapter, sample_config):
        """Test complete save and load roundtrip preserves all data."""
        await adapter.save_config(sample_config)
        loaded_config = await adapter.load_latest_config()

        # Compare all fields
        assert len(loaded_config.circuits) == len(sample_config.circuits)
        for i, circuit in enumerate(sample_config.circuits):
            loaded_circuit = loaded_config.circuits[i]
            assert loaded_circuit.circuit_id == circuit.circuit_id
            assert loaded_circuit.name == circuit.name
            assert loaded_circuit.temp_comfort == circuit.temp_comfort
            assert loaded_circuit.temp_normal == circuit.temp_normal
            assert loaded_circuit.temp_reduced == circuit.temp_reduced

        assert loaded_config.dhw is not None
        assert sample_config.dhw is not None
        assert loaded_config.dhw.active == sample_config.dhw.active
        assert loaded_config.dhw.temp_target == sample_config.dhw.temp_target

    @pytest.mark.asyncio
    async def test_multiple_adapters_same_database(self, temp_db_path, sample_config):
        """Test multiple adapter instances can work with the same database."""
        adapter1 = SqliteAdapter(db_path=temp_db_path)
        adapter2 = SqliteAdapter(db_path=temp_db_path)

        await adapter1.save_config(sample_config)
        loaded_config = await adapter2.load_latest_config()

        assert loaded_config is not None
        assert loaded_config.circuits[0].name == "Living Room"

    def test_database_autoincrement(self, adapter, sample_config):
        """Test that database ID autoincrement works correctly."""
        # We need to modify the config slightly to ensure it's saved
        # because the adapter now checks for changes before saving

        # Save 1
        adapter._save_config_sync(sample_config)

        # Save 2 (modified)
        sample_config.circuits[0].temp_comfort = 23.0
        adapter._save_config_sync(sample_config)

        # Save 3 (modified again)
        sample_config.circuits[0].temp_comfort = 24.0
        adapter._save_config_sync(sample_config)

        with sqlite3.connect(adapter.db_path) as conn:
            cursor = conn.execute("SELECT id FROM configs ORDER BY id")
            ids = [row[0] for row in cursor.fetchall()]

            assert ids == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_json_serialization_special_characters(self, adapter):
        """Test that special characters in config are handled correctly."""
        config = HeatPumpConfig(
            circuits=[
                CircuitConfig(
                    circuit_id=0,
                    name="Room with \"quotes\" and 'apostrophes' & symbols",
                )
            ]
        )
        await adapter.save_config(config)

        loaded_config = await adapter.load_latest_config()

        assert loaded_config is not None
        assert loaded_config.circuits[0].name == "Room with \"quotes\" and 'apostrophes' & symbols"

    @pytest.mark.asyncio
    async def test_save_changelog_entry(self, adapter):
        """Test saving a changelog entry."""
        from heatpump_stats.domain.metrics import ChangelogEntry

        entry = ChangelogEntry(
            category="note",
            author="user",
            message="Test note",
            details="Some details",
        )
        await adapter.save_changelog_entry(entry)

        with sqlite3.connect(adapter.db_path) as conn:
            cursor = conn.execute("SELECT category, message FROM changelog")
            row = cursor.fetchone()
            assert row[0] == "note"
            assert row[1] == "Test note"

    @pytest.mark.asyncio
    async def test_get_changelog(self, adapter):
        """Test retrieving changelog entries."""
        from heatpump_stats.domain.metrics import ChangelogEntry

        entry1 = ChangelogEntry(category="note", author="user", message="Note 1")
        entry2 = ChangelogEntry(category="system", author="system", message="Event 2")

        await adapter.save_changelog_entry(entry1)
        await adapter.save_changelog_entry(entry2)

        entries = await adapter.get_changelog()
        assert len(entries) == 2
        # Should be ordered by timestamp DESC (latest first)
        assert entries[0].message == "Event 2"
        assert entries[1].message == "Note 1"

    @pytest.mark.asyncio
    async def test_get_changelog_filtering(self, adapter):
        """Test filtering changelog entries by category."""
        from heatpump_stats.domain.metrics import ChangelogEntry

        entry1 = ChangelogEntry(category="note", author="user", message="Note 1")
        entry2 = ChangelogEntry(category="system", author="system", message="Event 2")
        entry3 = ChangelogEntry(category="note", author="user", message="Note 3")

        await adapter.save_changelog_entry(entry1)
        await adapter.save_changelog_entry(entry2)
        await adapter.save_changelog_entry(entry3)

        # Filter by 'note'
        notes = await adapter.get_changelog(category="note")
        assert len(notes) == 2
        assert all(e.category == "note" for e in notes)
        assert notes[0].message == "Note 3"
        assert notes[1].message == "Note 1"

        # Filter by 'system'
        system_events = await adapter.get_changelog(category="system")
        assert len(system_events) == 1
        assert system_events[0].category == "system"
        assert system_events[0].message == "Event 2"

        # Filter by non-existent category
        empty = await adapter.get_changelog(category="nonexistent")
        assert len(empty) == 0

    @pytest.mark.asyncio
    async def test_save_config_creates_changelog(self, adapter, sample_config):
        """Test that saving a config creates a changelog entry."""
        await adapter.save_config(sample_config)

        entries = await adapter.get_changelog()
        assert len(entries) == 1
        assert entries[0].category == "config"
        assert entries[0].message == "Configuration change detected"

    @pytest.mark.asyncio
    async def test_save_config_creates_changelog_with_details(self, adapter, sample_config):
        """Test that saving a config creates a changelog entry with details."""
        # Initial save
        await adapter.save_config(sample_config)
        
        # Modify config
        sample_config.circuits[0].temp_comfort = 25.0
        await adapter.save_config(sample_config)

        entries = await adapter.get_changelog()
        # Should have 2 entries: Initial and Update
        assert len(entries) == 2
        
        # Check latest entry (Update)
        latest = entries[0]
        assert latest.category == "config"
        assert latest.details is not None
        assert "circuits" in latest.details
        assert "25.0" in latest.details
        
        # Check initial entry
        initial = entries[1]
        assert initial.details == "Initial configuration"
