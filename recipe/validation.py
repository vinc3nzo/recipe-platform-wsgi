"""
This is disgusting, but I have to use v1 models.
My reasoning behind this is down below.

My brief research showed that:
[-] the support of `pydantic` v2 was added in
    `spectree` v. 1.2.0, dated 18th of July 2023.
    It is mentioned as a feature on the pypi page.
[-] the previous version of `spectree` (v. 1.1.5)
    does not mention anything related to this.
[-] skimming through the `spectree` source files
    revealed that they currently intentionally avoid
    `pydantic` v2 by doing a version check. If v2 is
    detected, they import `pydantic.v1` entities.

In conclusion, they lie about `pydantic` v2 models
support on the pypi page.

P.S.
    I tried importing the v2 classes for use inside of
    the `spectree` library, but it lead to a bunch
    of error messages appearing and an exception raising.
"""

from pydantic.version import VERSION as PYDANTIC_VERSION

PYDANTIC2 = PYDANTIC_VERSION.startswith("2")

if PYDANTIC2:
    from pydantic.v1 import BaseModel, Field, constr
else:
    from pydantic import BaseModel, Field, constr

from uuid import UUID

DEFAULT_PAGE_SIZE: int = 20
MAX_PAGE_SIZE: int = 50

# Database entity creation models

class RecipeCreate(BaseModel):
    source: str
    author_id: UUID

class UserCreate(BaseModel):
    username: str
    first_name: str
    last_name: str
    role: int | None = 0

class TagCreate(BaseModel):
    text: str

class BookmarkedRecipeCreate(BaseModel):
    user_id: UUID
    recipe_id: UUID

class RatedRecipeCreate(BaseModel):
    user_id: UUID
    recipe_id: UUID
    score: float

class RecipesTagsCreate(BaseModel):
    recipe_id: UUID
    tag_id: UUID

class StatusChange(BaseModel):
    status: int = Field(None, ge=0, le=2)

class UserPasswordCreate(BaseModel):
    user_id: UUID
    hashed_password: bytes

# Request and response models (for `spectree`)

from typing import Any

class ResponseWrapper(BaseModel):
    value: Any
    errors: list[str] | None = None

INTERNAL_ERROR_RESPONSE = ResponseWrapper(value=None, errors=['Something really bad just happened...'])

class PaginationParams(BaseModel):
    page: int | None = Field(default=1, ge=1)
    elements: int | None = Field(default=1, ge=1, le=MAX_PAGE_SIZE)

class PaginatedResponse(BaseModel):
    totalPages: int
    data: list[Any]

class UserData(BaseModel):
    id: UUID
    username: str
    first_name: str
    last_name: str
    date_registered: float
    role: int

class RecipeData(BaseModel):
    id: UUID
    source: str
    author_id: UUID
    date_created: float
    date_edited: float
    rating: float
    status: int
    bookmarked: bool
    user_score: float | None = Field(default=None, ge=1, le=5)

    def __init__(self, r, bookmarked: bool, user_score: float | None = None):
        self.id = r.id
        self.source = r.source
        self.author_id = r.author_id
        self.date_created = r.date_created
        self.date_edited = r.date_edited
        self.rating = r.rating
        self.status = r.status
        self.bookmarked = bookmarked
        self.user_score = user_score

class ErrorResponse(BaseModel):
    value: None
    errors: list[str]

class LoginRequest(BaseModel):
    username: constr(min_length=1, max_length=64)
    password: constr(min_length=1, max_length=128)

class RegistrationRequest(BaseModel):
    username: constr(min_length=1, max_length=64)
    password: constr(min_length=1, max_length=128)
    first_name: constr(min_length=1, max_length=64)
    last_name: constr(min_length=1, max_length=64)