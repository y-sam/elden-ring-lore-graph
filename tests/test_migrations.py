from pathlib import Path

import pytest

from elden_lore_api.migrations import load_migrations


def test_load_migrations_orders_and_hashes_files(tmp_path: Path) -> None:
    (tmp_path / "002_second.cypher").write_text("RETURN 2", encoding="utf-8")
    (tmp_path / "001_first.cypher").write_text("RETURN 1", encoding="utf-8")
    (tmp_path / "._001_first.cypher").write_bytes(b"AppleDouble metadata")

    migrations = load_migrations(tmp_path)

    assert [migration.version for migration in migrations] == ["001", "002"]
    assert all(len(migration.checksum) == 64 for migration in migrations)


def test_load_migrations_rejects_invalid_names(tmp_path: Path) -> None:
    (tmp_path / "initial.cypher").write_text("RETURN 1", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid migration filename"):
        load_migrations(tmp_path)
