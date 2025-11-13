from pydantic import BaseModel


class Content(BaseModel):
    id: str
    course_id: str
    title: str


