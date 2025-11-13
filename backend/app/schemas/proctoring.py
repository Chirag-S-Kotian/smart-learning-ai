from pydantic import BaseModel


class ProctoringSessionCreate(BaseModel):
    assessment_id: str


class ProctoringSessionRead(BaseModel):
    id: str
    assessment_id: str
    status: str


