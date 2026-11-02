CREATE CONSTRAINT migration_version_unique IF NOT EXISTS
FOR (m:_Migration) REQUIRE m.version IS UNIQUE
