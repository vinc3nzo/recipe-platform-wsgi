import falcon
from falcon import Request, Response

from sqlalchemy import select, func
from sqlalchemy.orm import sessionmaker, Session

from ..util import check_auth
from ..database.models import BookmarkedRecipe, RatedRecipe, Recipe, Status
from ..validation import (
    BookmarkedRecipeCreate, ResponseWrapper, INTERNAL_ERROR_RESPONSE,
    PaginationParams, PaginatedRecipeResponse, ErrorResponse, RecipeData
)
from ..log import logging
from ..spec import api

from uuid import UUID
import math

from spectree import Response as SpecResponse

class BookmarkResource:

    db_session: sessionmaker[Session]

    def __init__(self, db_sessionmaker: sessionmaker[Session]):
        self.db_session = db_sessionmaker

    @api.validate(
        query=PaginationParams,
        resp=SpecResponse(
            HTTP_200=PaginatedRecipeResponse,
            HTTP_401=ErrorResponse,
            HTTP_403=ErrorResponse,
            HTTP_500=ErrorResponse
        ),
    )
    @falcon.before(check_auth)
    def on_get(self, req: Request, resp: Response):
        try:
            page: int = req.context.query.page
            elements: int = req.context.query.elements
            user_id: UUID = req.context.user_id

            with self.db_session() as db:
                records = db.scalars(select(BookmarkedRecipe)
                                    .where(BookmarkedRecipe.user_id == user_id)
                                    .order_by(BookmarkedRecipe.date_added.desc())
                                    .offset((page - 1) * elements)
                                    .limit(elements)).all()
                
                recipe_ids = [rec.recipe_id for rec in records]

                recipes = db.scalars(select(Recipe).where(Recipe.id.in_(recipe_ids))).all()

                res_data = []
                for recipe in recipes:
                    rating_record = db.scalar(select(RatedRecipe).where((RatedRecipe.recipe_id == recipe.id) & (RatedRecipe.user_id == user_id)))

                    data = RecipeData(
                        id=recipe.id,
                        source=recipe.source,
                        author_id=recipe.author_id,
                        date_created=recipe.date_created,
                        date_edited=recipe.date_edited,
                        rating=recipe.rating,
                        status=recipe.status,
                        bookmarked=True,
                        user_score=rating_record.score if rating_record is not None else None,
                    )

                    res_data.append(data)

                query = select(func.count()).select_from(BookmarkedRecipe)
                total_records: int = db.scalar(query)

                resp.media = {
                    'value': {
                        'totalPages': math.ceil(total_records / elements),
                        'data': [d.serialize() for d in res_data]
                    }
                }
        except Exception as e:
            resp.media = INTERNAL_ERROR_RESPONSE
            resp.status = falcon.HTTP_500
            logging.exception(e)

    @api.validate(
        resp=SpecResponse(
            HTTP_200=ErrorResponse,
            HTTP_201=ResponseWrapper,
            HTTP_401=ErrorResponse,
            HTTP_403=ErrorResponse,
            HTTP_404=ErrorResponse,
            HTTP_500=ErrorResponse
        ),
        path_parameter_descriptions={
            '_id': 'A UUID that corresponds to a recipe.'
        }
    )
    @falcon.before(check_auth)
    def on_post_bookmark(self, req: Request, resp: Response, _id: UUID):
        try:
            user_id: UUID = req.context.user_id
            recipe_id: UUID = _id

            with self.db_session() as db:
                existing_recipe = db.scalar(select(Recipe).where((Recipe.id == recipe_id) & (Recipe.status == Status.APPROVED)))

                if existing_recipe is None:
                    resp.media = {
                        'value': None,
                        'errors': ['There is no recipe with such id. Probably, the recipe haven\'t been approved by the moderators yet.']
                    }
                    resp.status = falcon.HTTP_404
                    return

                existing_bookmark = db.scalar(select(BookmarkedRecipe)
                                              .where((BookmarkedRecipe.recipe_id == recipe_id) & (BookmarkedRecipe.user_id == user_id)))
                if existing_bookmark is not None:
                    resp.media = {
                        'value': None,
                        'errors': ['The bookmark is already added.']
                    }
                    resp.status = falcon.HTTP_200
                    return

                c = BookmarkedRecipeCreate(
                    user_id=user_id,
                    recipe_id=recipe_id
                )

                bookmark = BookmarkedRecipe(c)

                db.add(bookmark)
                db.commit()
        
                resp.media = {
                    'value': None,
                    'error': None
                }
                resp.status = falcon.HTTP_201
        except Exception as e:
            resp.media = INTERNAL_ERROR_RESPONSE
            resp.status = falcon.HTTP_500
            logging.exception(e)

    @api.validate(
        resp=SpecResponse(
            HTTP_200=ResponseWrapper,
            HTTP_401=ErrorResponse,
            HTTP_403=ErrorResponse,
            HTTP_404=ErrorResponse,
            HTTP_500=ErrorResponse
        ),
        path_parameter_descriptions={
            '_id': 'A UUID that corresponds to a recipe.'
        }
    )
    @falcon.before(check_auth)
    def on_delete_bookmark(self, req: Request, resp: Response, _id: UUID):
        try:
            user_id: UUID = req.context.user_id
            recipe_id: UUID = _id

            with self.db_session() as db:
                bookmark = db.scalar(select(BookmarkedRecipe)
                                     .where((BookmarkedRecipe.user_id == user_id) & (BookmarkedRecipe.recipe_id == recipe_id)))
                if bookmark is None:
                    resp.media = {
                        'value': None,
                        'errors': ['Attempted to delete a non-existent bookmark.']
                    }
                    resp.status = falcon.HTTP_404
                    return
                
                db.delete(bookmark)
                db.commit()

                resp.media = {
                    'value': None,
                    'errors': None
                }
                resp.status = falcon.HTTP_200
        except Exception as e:
            resp.media = INTERNAL_ERROR_RESPONSE
            resp.status = falcon.HTTP_500
            logging.exception(e)