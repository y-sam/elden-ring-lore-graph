import argparse
from pathlib import Path
from typing import Any

from neo4j import Driver, ManagedTransaction

from elden_lore_api.config import get_settings
from elden_lore_api.curated import CuratedDataset, load_curated_dataset
from elden_lore_api.database import create_driver

DEFAULT_DATASET = (
    Path(__file__).parents[2] / "data" / "curated" / "the_shattering.seed.json"
)


def import_dataset(driver: Driver, dataset: CuratedDataset, database: str) -> dict[str, int]:
    payload = dataset.model_dump(mode="json")
    with driver.session(database=database) as session:
        return session.execute_write(_write_dataset, payload)


def _write_dataset(tx: ManagedTransaction, payload: dict[str, Any]) -> dict[str, int]:
    dataset = {
        "id": payload["dataset_id"],
        "version": payload["dataset_version"],
        "status": payload["status"],
    }
    tx.run(
        """
        MERGE (dataset:Dataset {id: $dataset.id})
        SET dataset.version = $dataset.version,
            dataset.status = $dataset.status,
            dataset.imported_at = datetime()
        """,
        dataset=dataset,
    ).consume()

    for label, key in (
        ("Entity", "entities"),
        ("Alias", "aliases"),
        ("Source", "sources"),
        ("Evidence", "evidence"),
        ("LocalizedText", "localized_texts"),
        ("Claim", "claims"),
    ):
        _prune_dataset_records(
            tx,
            dataset_id=payload["dataset_id"],
            label=label,
            current_ids=[row["id"] for row in payload[key]],
        )

    tx.run(
        """
        MATCH (dataset:Dataset {id: $dataset_id})
        UNWIND $rows AS row
        MERGE (entity:Entity {id: row.id})
        SET entity.kind = row.kind,
            entity.canonical_name = row.canonical_name,
            entity.continuity = row.continuity,
            entity.updated_at = datetime()
        MERGE (dataset)-[:INCLUDES]->(entity)
        """,
        dataset_id=payload["dataset_id"],
        rows=payload["entities"],
    ).consume()

    tx.run(
        """
        MATCH (dataset:Dataset {id: $dataset_id})
        UNWIND $rows AS row
        MERGE (alias:Alias {id: row.id})
        SET alias += row, alias.updated_at = datetime()
        REMOVE alias.entity_id
        MERGE (dataset)-[:INCLUDES]->(alias)
        WITH row, alias
        OPTIONAL MATCH (:Entity)-[old:HAS_ALIAS]->(alias)
        DELETE old
        WITH row, alias
        MATCH (entity:Entity {id: row.entity_id})
        MERGE (entity)-[:HAS_ALIAS]->(alias)
        """,
        dataset_id=payload["dataset_id"],
        rows=payload["aliases"],
    ).consume()

    tx.run(
        """
        MATCH (dataset:Dataset {id: $dataset_id})
        UNWIND $rows AS row
        MERGE (source:Source {id: row.id})
        SET source += row,
            source.updated_at = datetime()
        MERGE (dataset)-[:INCLUDES]->(source)
        """,
        dataset_id=payload["dataset_id"],
        rows=payload["sources"],
    ).consume()

    tx.run(
        """
        MATCH (dataset:Dataset {id: $dataset_id})
        UNWIND $rows AS row
        MERGE (evidence:Evidence {id: row.id})
        SET evidence += row,
            evidence.updated_at = datetime()
        MERGE (dataset)-[:INCLUDES]->(evidence)
        WITH row, evidence
        OPTIONAL MATCH (:Source)-[old:CONTAINS]->(evidence)
        DELETE old
        WITH row, evidence
        MATCH (source:Source {id: row.source_id})
        MERGE (source)-[:CONTAINS]->(evidence)
        """,
        dataset_id=payload["dataset_id"],
        rows=payload["evidence"],
    ).consume()

    tx.run(
        """
        MATCH (dataset:Dataset {id: $dataset_id})
        UNWIND $rows AS row
        MERGE (text:LocalizedText {id: row.id})
        SET text += row,
            text.updated_at = datetime()
        REMOVE text.evidence_id
        MERGE (dataset)-[:INCLUDES]->(text)
        WITH row, text
        OPTIONAL MATCH (:Evidence)-[old:HAS_TEXT]->(text)
        DELETE old
        WITH row, text
        MATCH (evidence:Evidence {id: row.evidence_id})
        MERGE (evidence)-[:HAS_TEXT]->(text)
        """,
        dataset_id=payload["dataset_id"],
        rows=payload["localized_texts"],
    ).consume()

    tx.run(
        """
        MATCH (dataset:Dataset {id: $dataset_id})
        UNWIND $rows AS row
        MERGE (claim:Claim {id: row.id})
        SET claim += row,
            claim.updated_at = datetime()
        REMOVE claim.subject_id, claim.object_id, claim.evidence_ids
        MERGE (dataset)-[:INCLUDES]->(claim)
        WITH row, claim
        OPTIONAL MATCH (claim)-[old:SUBJECT|OBJECT|SUPPORTED_BY]->()
        DELETE old
        """,
        dataset_id=payload["dataset_id"],
        rows=payload["claims"],
    ).consume()

    tx.run(
        """
        UNWIND $rows AS row
        MATCH (claim:Claim {id: row.id})
        MATCH (subject:Entity {id: row.subject_id})
        MERGE (claim)-[:SUBJECT]->(subject)
        WITH row, claim
        UNWIND row.evidence_ids AS evidence_id
        MATCH (evidence:Evidence {id: evidence_id})
        MERGE (claim)-[:SUPPORTED_BY]->(evidence)
        """,
        rows=payload["claims"],
    ).consume()

    tx.run(
        """
        UNWIND $rows AS row
        WITH row WHERE row.object_id IS NOT NULL
        MATCH (claim:Claim {id: row.id})
        MATCH (object:Entity {id: row.object_id})
        MERGE (claim)-[:OBJECT]->(object)
        """,
        rows=payload["claims"],
    ).consume()

    return {
        "entities": len(payload["entities"]),
        "aliases": len(payload["aliases"]),
        "sources": len(payload["sources"]),
        "evidence": len(payload["evidence"]),
        "localized_texts": len(payload["localized_texts"]),
        "claims": len(payload["claims"]),
    }


def _prune_dataset_records(
    tx: ManagedTransaction,
    *,
    dataset_id: str,
    label: str,
    current_ids: list[str],
) -> None:
    tx.run(
        f"""
        MATCH (dataset:Dataset {{id: $dataset_id}})-[included:INCLUDES]->(record:{label})
        WHERE NOT record.id IN $current_ids
        DELETE included
        WITH record
        WHERE NOT EXISTS {{ MATCH (:Dataset)-[:INCLUDES]->(record) }}
        DETACH DELETE record
        """,
        dataset_id=dataset_id,
        current_ids=current_ids,
    ).consume()


def run() -> None:
    parser = argparse.ArgumentParser(description="Import a validated curated lore dataset")
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_DATASET)
    args = parser.parse_args()

    settings = get_settings()
    dataset = load_curated_dataset(args.path)
    driver = create_driver(settings)
    try:
        counts = import_dataset(driver, dataset, settings.neo4j_database)
    finally:
        driver.close()
    print(
        f"Imported {dataset.dataset_id} v{dataset.dataset_version}: "
        + ", ".join(f"{name}={count}" for name, count in counts.items())
    )
