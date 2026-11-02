import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from neo4j import Driver

from elden_lore_api.config import get_settings
from elden_lore_api.database import create_driver

MIGRATION_NAME = re.compile(r"^(?P<version>\d{3})_[a-z0-9_]+\.cypher$")


@dataclass(frozen=True)
class Migration:
    version: str
    name: str
    checksum: str
    statement: str


def load_migrations(directory: Path) -> list[Migration]:
    migrations: list[Migration] = []
    for path in sorted(directory.glob("*.cypher")):
        # External macOS volumes may create AppleDouble metadata files next to
        # the real migration. They are not Cypher and must never be executed.
        if path.name.startswith("._"):
            continue
        match = MIGRATION_NAME.fullmatch(path.name)
        if match is None:
            raise ValueError(f"Invalid migration filename: {path.name}")
        statement = path.read_text(encoding="utf-8").strip()
        if not statement:
            raise ValueError(f"Migration is empty: {path.name}")
        migrations.append(
            Migration(
                version=match.group("version"),
                name=path.name,
                checksum=hashlib.sha256(statement.encode()).hexdigest(),
                statement=statement,
            )
        )
    return migrations


def apply_migrations(driver: Driver, directory: Path, database: str) -> list[str]:
    applied_now: list[str] = []
    with driver.session(database=database) as session:
        existing = {
            record["version"]: record["checksum"]
            for record in session.run(
                "MATCH (m:_Migration) RETURN m.version AS version, m.checksum AS checksum"
            )
        }

        for migration in load_migrations(directory):
            previous_checksum = existing.get(migration.version)
            if previous_checksum is not None:
                if previous_checksum != migration.checksum:
                    raise RuntimeError(
                        f"Migration {migration.version} changed after it was applied"
                    )
                continue

            session.run(migration.statement).consume()
            session.run(
                """
                CREATE (m:_Migration {
                  version: $version,
                  name: $name,
                  checksum: $checksum,
                  applied_at: datetime()
                })
                """,
                version=migration.version,
                name=migration.name,
                checksum=migration.checksum,
            ).consume()
            applied_now.append(migration.version)
    return applied_now


def run() -> None:
    settings = get_settings()
    directory = Path(__file__).parents[2] / "graph" / "v2" / "migrations"
    driver = create_driver(settings)
    try:
        applied = apply_migrations(driver, directory, settings.neo4j_database)
    finally:
        driver.close()
    if applied:
        print(f"Applied migrations: {', '.join(applied)}")
    else:
        print("Database is already up to date")
