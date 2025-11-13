from pydantic import BaseModel


class Assessment(BaseModel):
    id: str
    course_id: str
    title: str


