from sqlalchemy.orm import Session

from app.models.rfq_task import RFQTask


class RFQTaskRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, task: RFQTask) -> RFQTask:
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_by_id(self, task_id: str) -> RFQTask | None:
        return self.db.get(RFQTask, task_id)

    def get_by_id_for_owner(self, task_id: str, owner_id: str | None) -> RFQTask | None:
        task = self.get_by_id(task_id)
        if not task:
            return None
        if owner_id is not None and task.owner_id != owner_id:
            return None
        return task

    def update(self, task: RFQTask) -> RFQTask:
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def list_recent(
        self,
        limit: int = 20,
        unique_file_name: bool = True,
        owner_id: str | None = None,
    ) -> list[RFQTask]:
        fetch_limit = limit * 5 if unique_file_name else limit
        query = self.db.query(RFQTask)
        if owner_id is not None:
            query = query.filter(RFQTask.owner_id == owner_id)
        tasks = (
            query.order_by(RFQTask.created_at.desc())
            .limit(max(1, min(fetch_limit, 100)))
            .all()
        )
        if not unique_file_name:
            return tasks[:limit]

        seen: set[str] = set()
        unique: list[RFQTask] = []
        for task in tasks:
            if task.file_name in seen:
                continue
            seen.add(task.file_name)
            unique.append(task)
            if len(unique) >= limit:
                break
        return unique
