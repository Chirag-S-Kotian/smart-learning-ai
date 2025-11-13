from pydantic import BaseModel


class ProctoringSession(BaseModel):
    id: str
    assessment_id: str
    status: str


