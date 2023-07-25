from typing import Any

from pydantic import BaseModel

from uuid import UUID

from .database.models import Recipe

class GenericResponse(BaseModel):
    """Generic response incapsulates the response data as well
    as human-readable list of errors for easier debugging."""

    value: Any
    errors: list[str] = None

ERROR_RESPONSE = GenericResponse(value=None, errors=['Something really bad just happened...'])

class RecipeData:
    id: UUID
    source: str
    author_id: UUID
    date_created: float
    date_edited: float
    rating: float
    status: int
    bookmarked: bool
    user_score: float

    def __init__(self, r: Recipe, bookmarked: bool, user_score: float | None = None):
        self.id = r.id
        self.source = r.source
        self.author_id = r.author_id
        self.date_created = r.date_created
        self.date_edited = r.date_edited
        self.rating = r.rating
        self.status = r.status
        self.bookmarked = bookmarked
        self.user_score = user_score