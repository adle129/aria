from sqlalchemy import create_engine

from app.database import Base
from app.models.knowledge_index_generation import KnowledgeIndexGeneration, KnowledgeIndexState
from app.repositories.knowledge_generation_repository import KnowledgeGenerationRepository


def _repository() -> KnowledgeGenerationRepository:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        bind=engine,
        tables=[
            KnowledgeIndexGeneration.__table__,
            KnowledgeIndexState.__table__,
        ],
    )
    return KnowledgeGenerationRepository(engine)


def _validated(repo: KnowledgeGenerationRepository, generation_id: str) -> None:
    repo.create(
        generation_id=generation_id,
        namespace="production",
        embedding_model="nomic-embed-text",
        created_by_job_id="job-1",
        content_fingerprint=generation_id,
    )
    repo.mark_validated(generation_id, 10)


def test_activate_switches_pointer_and_retires_previous_generation():
    repo = _repository()
    _validated(repo, "generation-1")
    repo.activate("generation-1", "production")
    _validated(repo, "generation-2")

    previous = repo.activate("generation-2", "production")

    assert previous == "generation-1"
    assert repo.get_active_id("production") == "generation-2"
    assert repo.get("generation-1").status == "retired"
    assert repo.get("generation-2").status == "active"
    assert repo.protected_generation_ids("production") == {
        "generation-1",
        "generation-2",
    }


def test_unvalidated_generation_cannot_replace_active_pointer():
    repo = _repository()
    _validated(repo, "generation-1")
    repo.activate("generation-1", "production")
    repo.create(
        generation_id="generation-2",
        namespace="production",
        embedding_model="nomic-embed-text",
        created_by_job_id="job-2",
        content_fingerprint="two",
    )

    try:
        repo.activate("generation-2", "production")
    except ValueError:
        pass
    else:
        raise AssertionError("building generation was activated")

    assert repo.get_active_id("production") == "generation-1"


def test_cleanup_excludes_active_and_previous_generations():
    repo = _repository()
    _validated(repo, "generation-1")
    repo.activate("generation-1", "production")
    _validated(repo, "generation-2")
    repo.activate("generation-2", "production")
    _validated(repo, "generation-3")
    repo.activate("generation-3", "production")

    assert repo.retired_for_cleanup("production") == ["generation-1"]
