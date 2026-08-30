
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.project_knowledge import ProjectKnowledge


class ProjectKnowledgeRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_workspace_id(
        self,
        workspace_id: UUID,
    ) -> ProjectKnowledge | None:
        return (
            self.db.query(ProjectKnowledge)
            .filter(
                ProjectKnowledge.workspace_id == workspace_id,
            )
            .first()
        )

    def create(
        self,
        project_knowledge: ProjectKnowledge,
    ) -> ProjectKnowledge:
        self.db.add(project_knowledge)
        self.db.flush()
        self.db.refresh(project_knowledge)

        return project_knowledge


    def update(
        self,
        project_knowledge: ProjectKnowledge,
    ) -> ProjectKnowledge:
        self.db.flush()
        self.db.refresh(project_knowledge)

        return project_knowledge
