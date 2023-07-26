import falcon
from falcon import Request, Response

from sqlalchemy import select, func
from sqlalchemy.orm import sessionmaker, Session

from ..util import check_auth, pagination, serialize, require_fields
from ..database.models import BookmarkedRecipe, Recipe, Status
from ..validation import BookmarkedRecipeCreate, ResponseWrapper, INTERNAL_ERROR_RESPONSE
from ..log import logging

from uuid import UUID
import math


class BookmarkResource:

    db_session: sessionmaker[Session]

    def __init__(self, db_sessionmaker: sessionmaker[Session]):
        self.db_session = db_sessionmaker

    @falcon.before(check_auth)
    @falcon.before(pagination)
    def on_get(self, req: Request, resp: Response):
        try:
            page: int = req.context.page
            elements: int = req.context.elements
            user_id: UUID = req.context.user_id

            with self.db_session() as db:
                records = db.scalars(select(BookmarkedRecipe)
                                    .where(BookmarkedRecipe.user_id == user_id)
                                    .order_by(BookmarkedRecipe.date_added.desc())
                                    .offset((page - 1) * elements)
                                    .limit(elements)).all()
                
                recipe_ids = [rec.recipe_id for rec in records]

                recipes = db.scalars(select(Recipe).where(Recipe.id.in_(recipe_ids))).all()

                query = select(func.count()).select_from(BookmarkedRecipe)
                total_records: int = db.scalar(query)

                resp.media = serialize(ResponseWrapper(value={
                    'totalPages': math.ceil(total_records / elements),
                    'data': recipes
                }))
        except Exception as e:
            resp.media = INTERNAL_ERROR_RESPONSE
            resp.status = falcon.HTTP_500
            logging.exception(e)

    @falcon.before(check_auth)
    @falcon.before(require_fields, ['recipe_id'])
    def on_post(self, req: Request, resp: Response):
        try:
            user_id: UUID = req.context.user_id
            recipe_id: UUID = UUID(req.context.body['recipe_id'])

            with self.db_session() as db:
                existing_recipe = db.scalar(select(Recipe).where((Recipe.id == recipe_id) & (Recipe.status == Status.APPROVED)))

                if existing_recipe is None:
                    resp.media = serialize(ResponseWrapper(value=None, errors=['There is no recipe with such id. Probably, the recipe haven\'t been approved by the moderators yet.']))
                    resp.status = falcon.HTTP_404
                    return

                existing_bookmark = db.scalar(select(BookmarkedRecipe)
                                              .where((BookmarkedRecipe.recipe_id == recipe_id) & (BookmarkedRecipe.user_id == user_id)))
                if existing_bookmark is not None:
                    resp.media = serialize(ResponseWrapper(value=None, errors=['The bookmark is already added.']))
                    resp.status = falcon.HTTP_200
                    return

                c = BookmarkedRecipeCreate(
                    user_id=user_id,
                    recipe_id=recipe_id
                )

                bookmark = BookmarkedRecipe(c)

                db.add(bookmark)
                db.commit()
        
                resp.media = serialize(ResponseWrapper(value=None))
                resp.status = falcon.HTTP_201
        except Exception as e:
            resp.media = INTERNAL_ERROR_RESPONSE
            resp.status = falcon.HTTP_500
            logging.exception(e)

    @falcon.before(check_auth)
    @falcon.before(require_fields, ['recipe_id'])
    def on_delete(self, req: Request, resp: Response):
        try:
            user_id: UUID = req.context.user_id
            recipe_id: UUID = UUID(req.context.body['recipe_id'])

            with self.db_session() as db:
                bookmark = db.execute(select(BookmarkedRecipe)
                                    .where((BookmarkedRecipe.user_id == user_id) & (BookmarkedRecipe.recipe_id == recipe_id))).scalar()
                if bookmark is None:
                    resp.media = serialize(ResponseWrapper(value=None, errors=['Attempted to delete a non-existent bookmark.']))
                    resp.status = falcon.HTTP_200
                    return
                
                db.delete(bookmark)
                db.commit()

                resp.media = serialize(ResponseWrapper(value=None))
                resp.status = falcon.HTTP_200
        except Exception as e:
            resp.media = INTERNAL_ERROR_RESPONSE
            resp.status = falcon.HTTP_500
            logging.exception(e)