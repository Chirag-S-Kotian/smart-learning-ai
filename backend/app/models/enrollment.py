from pydantic import BaseModel


class Enrollment(BaseModel):
    id: str
    user_id: str
    course_id: str


