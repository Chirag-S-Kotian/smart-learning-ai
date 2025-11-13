from pydantic import BaseModel


class EnrollmentCreate(BaseModel):
    user_id: str
    course_id: str


class EnrollmentRead(BaseModel):
    id: str
    user_id: str
    course_id: str


