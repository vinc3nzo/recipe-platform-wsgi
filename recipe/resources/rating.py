import falcon
from falcon import Request, Response

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker, Session

from uuid import UUID

from ..database.models import RatedRecipe, Recipe
from ..validation import RatedRecipeCreate, ResponseWrapper, INTERNAL_ERROR_RESPONSE
from ..util import require_auth, serialize, require_fields
from ..log import logging

class RatingResource:
    
    db_session: sessionmaker[Session]

    def __init__(self, db_sessionmaker: sessionmaker[Session]):
        self.db_session = db_sessionmaker

    @falcon.before(require_auth)
    def on_get(self, req: Request, resp: Response, _id: UUID):
        try:
            with self.db_session() as db:
                recipe = db.scalar(select(Recipe).where(Recipe.id == _id))

                if recipe is None:
                    resp.media = serialize(ResponseWrapper(value=None, errors=['There is no recipe with such id.']))
                    resp.status = falcon.HTTP_404
                    return
                
                resp.media = serialize(ResponseWrapper(
                    value={
                        'rating': recipe.rating
                    }
                ))
                resp.status = falcon.HTTP_200

        except Exception as e:
            resp.media = serialize(INTERNAL_ERROR_RESPONSE)
            resp.status = falcon.HTTP_500
            logging.exception(e)
    
    @falcon.before(require_auth)
    @falcon.before(require_fields, ['score'])
    def on_post(self, req: Request, resp: Response, _id: UUID):
        try:
            user_id: UUID = req.context.user_id
            score: float = req.context.body['score']

            with self.db_session() as db:
                recipe = db.scalar(select(Recipe).where(Recipe.id == _id))

                if recipe is None:
                    resp.media = serialize(ResponseWrapper(value=None, errors=['There is no recipe with such id.']))
                    resp.status = falcon.HTTP_404
                    return
                
                existing_rating = db.scalar(select(RatedRecipe)
                                            .where((RatedRecipe.recipe_id == _id) & (RatedRecipe.user_id == user_id)))

                if score < 1 or score > 5:
                    resp.media = serialize(ResponseWrapper(value=None, errors=['The score must be a float value in range [1; 5].']))
                    resp.status = falcon.HTTP_400
                    return
                
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

                resp.media = serialize(ResponseWrapper(value=None))
                resp.status = falcon.HTTP_200

        except Exception as e:
            resp.media = serialize(INTERNAL_ERROR_RESPONSE)
            resp.status = falcon.HTTP_500
            logging.exception(e)