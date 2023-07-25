from pydantic import BaseModel
from pydantic import Field

from uuid import UUID

# Pydantic models

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
    