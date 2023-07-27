import falcon
from falcon import Request, Response

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker, Session

from spectree import Response as SpecResponse

import uuid
from uuid import UUID

import os
import io
import PIL.Image
import pathlib

from datetime import datetime

from ..database.models import ImageConfig, Image, Recipe
from ..util import check_auth
from ..validation import (
    ImageCreate, INTERNAL_ERROR_RESPONSE, ErrorResponse
)
from ..log import logging
from ..spec import api

class ImageStore:

    _config: ImageConfig
    db_session: sessionmaker[Session]

    def __init__(self, db_sessionmaker: sessionmaker[Session], config: ImageConfig):
        self._config = config
        self.db_session = db_sessionmaker

    def _load_from_bytes(self, data):
        return PIL.Image.open(io.BytesIO(data))

    def _convert(self, image: PIL.Image):
        rgb_image = image.convert('RGB')

        converted = io.BytesIO()
        rgb_image.save(converted, 'JPEG')
        return converted.getvalue()

    def get_all(self, recipe_id: UUID) -> list[Image] | None:
        with self.db_session() as db:
            recipe = db.scalar(select(Recipe).where(Recipe.id == recipe_id))
            if recipe is None:
                return None

            images = db.scalars(select(Image).where(Image.recipe_id == recipe_id)).all()
            return images

    def get(self, recipe_id: UUID, image_id: UUID) -> Image | None:
        with self.db_session() as db:
            image_record = db.scalar(select(Image)
                                     .where((Image.recipe_id == recipe_id) & (Image.image_id == image_id)))
            return image_record

    def save(self, recipe_id: UUID, image_id: UUID, data) -> Image | None:
        with self.db_session() as db:
            recipe = db.scalar(select(Recipe).where(Recipe.id == recipe_id))
            if recipe is None:
                return None

        image = self._load_from_bytes(data)
        converted = self._convert(image)

        path = self._config.storage_path / (str(recipe_id) + '_' + str(image_id))
        with io.open(path, 'wb') as output:
            output.write(converted)

        c = ImageCreate(
            image_id=image_id,
            recipe_id=recipe_id,
            size=image.size
        )

        stored = Image(c, self._config)
        
        with self.db_session() as db:
            db.add(stored)
            db.commit()
            return stored


class ImageResource:

    _config: ImageConfig
    _store: ImageStore

    def __init__(self, config: ImageConfig, store: ImageStore):
        self._config = config
        self._store = store

    def on_get(self, req: Request, resp: Response, recipe_id: UUID):
        images = self._store.get_all(recipe_id)
        if images is None:
            resp.media = {
                'value': None,
                'errors': ['There is no recipe with such id.']
            }
            resp.status = falcon.HTTP_404
            return

        resp.media = {
            'value': [
                image.serialize() for image in images
            ],
            'errors': None
        }
        resp.status = falcon.HTTP_200

    def on_post(self, req: Request, resp: Response, recipe_id: UUID):
        data = req.stream.read()
        image_id = self._config.uuid_generator()
        image = self._store.save(recipe_id, image_id, data)

        if image is None:
            resp.status = falcon.HTTP_404
            resp.media = {
                'value': None,
                'errors': ['There is no recipe with such id.']
            }
            return

        resp.location = image.uri
        resp.media = {
            'value': image.serialize(),
            'errors': None
        }
        resp.status = falcon.HTTP_201

    def on_get_image(self, req: Request, resp: Response, recipe_id: UUID, image_id: UUID):
        image = self._store.get(recipe_id, image_id)

        if image is None:
            resp.content_type = falcon.MEDIA_JPEG
            resp.status = falcon.HTTP_404
            return

        resp.stream = io.open(image.path, 'rb')
        resp.content_type = falcon.MEDIA_JPEG