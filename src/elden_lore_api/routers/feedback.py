from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from neo4j import Driver

from elden_lore_api.api_models import FeedbackCreate, FeedbackReceipt, FeedbackSummary
from elden_lore_api.config import get_settings
from elden_lore_api.feedback import FeedbackRepository

router = APIRouter(prefix="/feedback", tags=["feedback"])


def get_feedback_repository(request: Request) -> FeedbackRepository:
    driver: Driver | None = getattr(request.app.state, "neo4j_driver", None)
    if driver is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j driver is not initialized",
        )
    return FeedbackRepository(driver, get_settings().neo4j_database)


Repository = Annotated[FeedbackRepository, Depends(get_feedback_repository)]


@router.post("", response_model=FeedbackReceipt, status_code=status.HTTP_201_CREATED)
def create_feedback(payload: FeedbackCreate, repository: Repository) -> FeedbackReceipt:
    return repository.create(payload)


@router.get("/{answer_id}", response_model=FeedbackSummary)
def get_feedback_summary(answer_id: str, repository: Repository) -> FeedbackSummary:
    return repository.summary(answer_id)
