import falcon
from falcon import Request, Response

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker, Session

from uuid import UUID

from ..database.models import RatedRecipe, Recipe
from ..validation import (
    RatedRecipeCreate, ResponseWrapper, INTERNAL_ERROR_RESPONSE,
    RatingResponse, RatingRequest, ErrorResponse, PaginationParams
)
from ..util import check_auth
from ..log import logging
from ..spec import api

from spectree import Response as SpecResponse

class RatingResource:
    
    db_session: sessionmaker[Session]

    def __init__(self, db_sessionmaker: sessionmaker[Session]):
        self.db_session = db_sessionmaker

    @api.validate(
        resp=SpecResponse(
            HTTP_200=RatingResponse,
            HTTP_401=ErrorResponse,
            HTTP_403=ErrorResponse,
            HTTP_404=ErrorResponse,
            HTTP_500=ErrorResponse
        ),
        query=PaginationParams,
        path_parameter_descriptions={
            '_id': 'A UUID that corresponds to a recipe.'
        }
    )
    @falcon.before(check_auth)
    def on_get(self, req: Request, resp: Response, _id: UUID):
        try:
            with self.db_session() as db:
                recipe = db.scalar(select(Recipe).where(Recipe.id == _id))

                if recipe is None:
                    resp.media = {
                        'value': None,
                        'errors': ['There is no recipe with such id.']
                    }
                    resp.status = falcon.HTTP_404
                    return
                
                resp.media = {
                    'value': {
                        'rating': recipe.rating
                    },
                    'errors': None
                }
                resp.status = falcon.HTTP_200

        except Exception as e:
            resp.media = INTERNAL_ERROR_RESPONSE
            resp.status = falcon.HTTP_500
            logging.exception(e)
    
    @api.validate(
        resp=SpecResponse(
            HTTP_201=ResponseWrapper,
            HTTP_401=ErrorResponse,
            HTTP_403=ErrorResponse,
            HTTP_404=ErrorResponse,
            HTTP_500=ErrorResponse
        ),
        query=PaginationParams,
        json=RatingRequest,
        path_parameter_descriptions={
            '_id': 'A UUID that corresponds to a recipe.'
        }
    )
    @falcon.before(check_auth)
    def on_post(self, req: Request, resp: Response, _id: UUID):
        try:
            user_id: UUID = req.context.user_id
            score: float = req.context.json.score

            with self.db_session() as db:
                recipe = db.scalar(select(Recipe).where(Recipe.id == _id))

                if recipe is None:
                    resp.media = {
                        'value': None,
                        'errors': ['There is no recipe with such id.']
                    }
                    resp.status = falcon.HTTP_404
                    return
                
                existing_rating = db.scalar(select(RatedRecipe)
                                            .where((RatedRecipe.recipe_id == _id) & (RatedRecipe.user_id == user_id)))
                
                if existing_rating is not None:
                    db.delete(existing_rating)
                    db.commit()

                ratings = db.scalars(select(RatedRecipe).where(RatedRecipe.recipe_id == _id)).all()

                c = RatedRecipeCreate(
                    user_id=user_id,
                    recipe_id=_id,
                    score=score
                )
                rating_record = RatedRecipe(c)
                db.add(rating_record)

                recipe.rating = (sum([record.score for record in ratings]) + score) / (len(ratings) + 1)
                db.add(recipe)
                db.commit()

                resp.media = {
                    'value': None,
                    'errors': None
                }
                resp.status = falcon.HTTP_201

        except Exception as e:
            resp.media = INTERNAL_ERROR_RESPONSE
            resp.status = falcon.HTTP_500
            logging.exception(e)