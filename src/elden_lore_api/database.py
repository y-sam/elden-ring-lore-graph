from collections.abc import Iterator

from neo4j import Driver, GraphDatabase

from elden_lore_api.config import Settings, get_settings


def create_driver(settings: Settings | None = None) -> Driver:
    config = settings or get_settings()
    return GraphDatabase.driver(
        config.neo4j_uri,
        auth=(config.neo4j_username, config.neo4j_password),
    )


def driver_lifespan(settings: Settings | None = None) -> Iterator[Driver]:
    driver = create_driver(settings)
    try:
        yield driver
    finally:
        driver.close()
