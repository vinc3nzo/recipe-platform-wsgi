import falcon
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from typing import Any
from uuid import UUID, uuid4
from datetime import datetime

import pathlib
import os

from ..validation import (
    ImageCreate, UserCreate, RecipeCreate, TagCreate, BookmarkedRecipeCreate,
    RatedRecipeCreate, RecipesTagsCreate, UserPasswordCreate
)

# SQLAlchemy ORM models

class OrmBase(DeclarativeBase):
    pass

class Authority:
    USER = 1
    MODERATOR = 2
    ADMIN = 4

class User(OrmBase):
    __tablename__ = 'users'

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(nullable=False)
    first_name: Mapped[str] = mapped_column(nullable=False)
    last_name: Mapped[str] = mapped_column(nullable=False)
    date_registered: Mapped[datetime] = mapped_column(nullable=False)
    role: Mapped[int] = mapped_column(nullable=False)

    def __init__(self, c: UserCreate):
        self.username = c.username
        self.first_name = c.first_name
        self.last_name = c.last_name
        self.date_registered = datetime.utcnow()
        self.role = c.role or Authority.USER
    
    def serialize(self) -> dict[str, Any]:
        return {
            'id': str(self.id),
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'date_registered': falcon.dt_to_http(self.date_registered),
            'role': self.role
        }

class Status:
    DENIED: int = 0
    PENDING: int = 1
    APPROVED: int = 2

class Recipe(OrmBase):
    __tablename__ = 'recipes'

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column(nullable=False)
    author_id: Mapped[UUID] = mapped_column(nullable=False)
    date_created: Mapped[datetime] = mapped_column(nullable=False)
    date_edited: Mapped[datetime] = mapped_column(nullable=False)
    rating: Mapped[float] = mapped_column(nullable=False)
    status: Mapped[int] = mapped_column(nullable=False)

    def __init__(self, c: RecipeCreate):
        self.source = c.source
        self.author_id = c.author_id
        self.date_created = datetime.utcnow()
        self.date_edited = datetime.utcnow()
        self.rating = 0
        self.status = Status.PENDING

    def serialize(self) -> dict[str, Any]:
        return {
            'id': str(self.id),
            'source': self.source,
            'author_id': str(self.author_id),
            'date_created': falcon.dt_to_http(self.date_created),
            'date_edited': falcon.dt_to_http(self.date_edited),
            'rating': self.rating,
            'status': self.status
        }

class Tag(OrmBase):
    __tablename__ = 'tags'

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    text: Mapped[str] = mapped_column(nullable=False)

    def __init__(self, c: TagCreate):
        self.text = c.text

class ImageConfig:
    DEFAULT_IMAGE_STORE_PATH = '/var/www/recipe-platform/img'
    DEFAULT_UUID_GENERATOR = uuid4

    def __init__(self):
        self.storage_path = pathlib.Path(
            os.environ.get('IMAGE_STORE_PATH', self.DEFAULT_IMAGE_STORE_PATH)
        )
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.uuid_generator = ImageConfig.DEFAULT_UUID_GENERATOR

class Image:
    __tablename__ = 'images'

    _config: ImageConfig

    image_id: Mapped[UUID] = mapped_column(primary_key=True, nullable=False)
    recipe_id: Mapped[UUID] = mapped_column(nullable=False)
    size: Mapped[int] = mapped_column(nullable=False)
    date_added: Mapped[datetime] = mapped_column(nullable=False)

    def __init__(self, c: ImageCreate, config: ImageConfig):
        self._config = config
        self.image_id = c.image_id
        self.recipe_id = c.recipe_id
        self.size = c.size
        self.date_added = datetime.utcnow()

    @property
    def path(self):
        return self._config.storage_path / self.image_id

    @property
    def uri(self):
        return f'/recipe/{self.recipe_id}/image/{self.image_id}'

    def serialize(self):
        return {
            'image_id': self.image_id,
            'recipe_id': self.recipe_id,
            'href': self.uri,
            'modified': falcon.dt_to_http(self.date_added),
            'size': self.size,
        }

# Associations table for the many-to-many relationships

class BookmarkedRecipe(OrmBase):
    __tablename__ = 'bookmarked_recipes'

    user_id: Mapped[UUID] = mapped_column(primary_key=True, nullable=False)
    recipe_id: Mapped[UUID] = mapped_column(primary_key=True, nullable=False)
    date_added: Mapped[datetime] = mapped_column(nullable=False)

    def __init__(self, c: BookmarkedRecipeCreate):
        self.user_id = c.user_id
        self.recipe_id = c.recipe_id
        self.date_added = datetime.utcnow()

class RatedRecipe(OrmBase):
    __tablename__ = 'rated_recipes'

    user_id: Mapped[UUID] = mapped_column(primary_key=True, nullable=False)
    recipe_id: Mapped[UUID] = mapped_column(primary_key=True, nullable=False)
    score: Mapped[float] = mapped_column(nullable=False)

    def __init__(self, c: RatedRecipeCreate):
        self.user_id = c.user_id
        self.recipe_id = c.recipe_id
        self.score = c.score

class RecipesTags(OrmBase):
    __tablename__ = 'recipes_tags'

    recipe_id: Mapped[UUID] = mapped_column(primary_key=True, nullable=False)
    tag_id: Mapped[UUID] = mapped_column(primary_key=True, nullable=False)

    def __init__(self, c: RecipesTagsCreate):
        self.recipe_id = c.recipe_id
        self.tag_id = c.tag_id

# Associations table for the one-to-one relationships

class UserPassword(OrmBase):
    __tablename__ = 'user_password'

    user_id: Mapped[UUID] = mapped_column(primary_key=True, nullable=False)
    hashed_password: Mapped[bytes] = mapped_column(nullable=False)

    def __init__(self, c: UserPasswordCreate):
        self.user_id = c.user_id
        self.hashed_password = c.hashed_password