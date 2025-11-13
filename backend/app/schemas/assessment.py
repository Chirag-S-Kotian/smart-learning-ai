from pydantic import BaseModel


class AssessmentCreate(BaseModel):
    course_id: str
    title: str


class AssessmentRead(BaseModel):
    id: str
    course_id: str
    title: str


