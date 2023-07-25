import falcon
from falcon import Request, Response

from sqlalchemy import select, func
from sqlalchemy.orm import sessionmaker, Session

from ..util import pagination, require_auth, serialize, require_fields
from ..response import ERROR_RESPONSE, GenericResponse, RecipeData

from ..database.models import Recipe, Tag, RecipesTags, Status, Authority, BookmarkedRecipe, RatedRecipe
from ..database.validation import RecipeCreate, TagCreate, RecipesTagsCreate, StatusChange

from ..log import logging

import math
from uuid import UUID

class RecipeResource:

    db_session: sessionmaker[Session]

    def __init__(self, db_sessionmaker: sessionmaker):
        self.db_session = db_sessionmaker

    @falcon.before(require_auth)
    @falcon.before(pagination)
    def on_get(self, req: Request, resp: Response):
        try:
            page: int = req.context.page
            elements: int = req.context.elements
            user_id: UUID = req.context.user_id

            with self.db_session() as db:
                recipes = db.scalars(select(Recipe)
                                     .where(Recipe.status == Status.APPROVED)
                                     .order_by(Recipe.rating.desc(), Recipe.date_created.asc())
                                     .offset((page - 1) * elements)
                                     .limit(elements)).all()

                res_data = []
                for recipe in recipes:
                    bookmark_record = db.scalar(select(BookmarkedRecipe).where((BookmarkedRecipe.recipe_id == recipe.id) & (BookmarkedRecipe.user_id == user_id)))
                    rating_record = db.scalar(select(RatedRecipe).where((RatedRecipe.recipe_id == recipe.id) & (RatedRecipe.user_id == user_id)))

                    data = RecipeData(
                        recipe,
                        bookmark_record is not None,
                        rating_record.score if rating_record is not None else None
                    )

                    res_data.append(data)

                query = select(func.count()).select_from(Recipe).where(Recipe.status == Status.APPROVED)
                total_records: int = db.scalar(query)

                resp.media = serialize(GenericResponse(value={
                    'totalPages': math.ceil(total_records / elements),
                    'data': res_data
                }))
                resp.status = falcon.HTTP_200

        except Exception as e:
            resp.media = serialize(ERROR_RESPONSE)
            resp.status = falcon.HTTP_500
            logging.exception(e)

    @falcon.before(require_auth)
    @falcon.before(require_fields, ['source'], ['tags'])
    def on_post(self, req: Request, resp: Response):
        try:
            with self.db_session() as db:
                c = RecipeCreate(
                    source=req.context.body['source'],
                    author_id=req.context.user_id
                )

                recipe = Recipe(c)

                db.add(recipe)
                db.commit()
                db.refresh(recipe)

                recipe_id = recipe.id

                # add tags, if any

                if req.context.body['tags'] is not None:
                    tags = req.context.body['tags']

                    for tag in tags:
                        existing_tag = db.scalar(select(Tag).where(Tag.text == tag))
                        if existing_tag is None:
                            c = TagCreate(text=tag)
                            new_tag = Tag(c)

                            db.add(new_tag)
                            db.commit()
                            db.refresh(new_tag) # need the ID

                            c = RecipesTagsCreate(
                                recipe_id=recipe_id,
                                tag_id=new_tag.id
                            )
                            new_record = RecipesTags(c)

                            db.add(new_record)
                            db.commit()

                resp.location = f'/recipe/{recipe_id}'
                resp.media = serialize(GenericResponse(value=None))
                resp.status = falcon.HTTP_201

        except Exception as e:
            resp.media = serialize(ERROR_RESPONSE)
            resp.status = falcon.HTTP_500
            logging.exception(e)

    @falcon.before(require_auth)
    def on_get_by_id(self, req: Request, resp: Response, _id: UUID):
        try:
            user_id: UUID = req.context.user_id

            with self.db_session() as db:
                result = db.execute(select(Recipe).where(Recipe.id == _id))
                recipe = result.scalar()

                if recipe is None:
                    resp.media = serialize(GenericResponse(value=None, errors=['No recipe with such id was found.']))
                    resp.status = falcon.HTTP_404
                    return
                
                bookmark_record = db.scalar(select(BookmarkedRecipe)
                                             .where((BookmarkedRecipe.user_id == user_id) & (BookmarkedRecipe.recipe_id == recipe.id)))
                rating_record = db.scalar(select(RatedRecipe)
                                           .where((RatedRecipe.user_id == user_id) & (RatedRecipe.recipe_id == recipe.id)))

                resp.media = serialize(GenericResponse(value=RecipeData(
                    recipe,
                    bookmark_record is not None,
                    rating_record.score if rating_record is not None else None
                )))
                resp.status = falcon.HTTP_200

        except Exception as e:
            resp.media = serialize(ERROR_RESPONSE)
            resp.status = falcon.HTTP_500
            logging.exception(e)

    @falcon.before(require_auth, Authority.MODERATOR)
    @falcon.before(require_fields, ['status'])
    def on_patch_by_id(self, req: Request, resp: Response, _id: UUID):
        try:
            user_id: UUID = req.context.user_id

            with self.db_session() as db:
                recipe = db.scalar(select(Recipe).where(Recipe.id == _id))

                if recipe is None:
                    resp.media = serialize(GenericResponse(value=None, errors=['No recipe with such id was found.']))
                    resp.status = falcon.HTTP_404
                    return

                c = StatusChange(status=req.context.body['status'])
                recipe.status = c.status

                db.add(recipe)
                db.commit()
                db.refresh(recipe)

                bookmark_record = db.scalar(select(BookmarkedRecipe)
                                            .where((BookmarkedRecipe.user_id == user_id) & (BookmarkedRecipe.recipe_id == recipe.id)))
                rating_record = db.scalar(select(RatedRecipe)
                                          .where((RatedRecipe.user_id == user_id) & (RatedRecipe.recipe_id == recipe.id)))

                resp.media = serialize(GenericResponse(value=RecipeData(
                    recipe,
                    bookmark_record is not None,
                    rating_record.score if rating_record is not None else None
                )))
                resp.status = falcon.HTTP_200

        except Exception as e:
            resp.media = serialize(ERROR_RESPONSE)
            resp.status = falcon.HTTP_500
            logging.exception(e)

    @falcon.before(require_auth)
    @falcon.before(pagination)
    def on_get_by_tags(self, req: Request, resp: Response):
        try:
            page: int = req.context.page
            elements: int = req.context.elements
            user_id: UUID = req.context.user_id

            search_query: str = req.params['q']
            tags = search_query.split()

            if len(tags) == 0:
                resp.media = serialize(ERROR_RESPONSE)
                resp.status = falcon.HTTP_500
                return

            with self.db_session() as db:
                results = db.scalars(select(Tag)
                                     .where(Tag.text.in_(tags)))
                
                tag_ids = [tag.id for tag in results]

                results = db.scalars(select(RecipesTags)
                                     .where(RecipesTags.tag_id.in_(tag_ids)))
                
                recipe_ids = [recipe_record.recipe_id for recipe_record in results]
                
                recipes = db.scalars(select(Recipe)
                                         .where(Recipe.id.in_(recipe_ids) & (Recipe.status == Status.APPROVED))
                                         .order_by(Recipe.rating.desc(), Recipe.date_created.asc())
                                         .offset((page - 1) * elements)
                                         .limit(elements)).all()

                res_data = []
                for recipe in recipes:
                    bookmark_record = db.execute(select(BookmarkedRecipe).where((BookmarkedRecipe.recipe_id == recipe.id) & (BookmarkedRecipe.user_id == user_id))).scalar()
                    rating_record = db.execute(select(RatedRecipe).where((RatedRecipe.recipe_id == recipe.id) & (RatedRecipe.user_id == user_id))).scalar()

                    data = RecipeData(
                        recipe,
                        bookmark_record is not None,
                        rating_record.score if rating_record is not None else None
                    )

                    res_data.append(data)

                query = select(func.count()).select_from(Recipe).where(Recipe.id.in_(recipe_ids) & (Recipe.status == Status.APPROVED))
                total_records: int = db.scalar(query)

                resp.media = serialize(GenericResponse(value={
                    'totalPages': math.ceil(total_records / elements),
                    'data': res_data
                }))
                resp.status = falcon.HTTP_200

        except Exception as e:
            resp.media = serialize(ERROR_RESPONSE)
            resp.status = falcon.HTTP_500
            logging.exception(e)

    @falcon.before(require_auth)
    @falcon.before(pagination)
    def on_get_my(self, req: Request, resp: Response):
        try:
            page: int = req.context.page
            elements: int = req.context.elements
            user_id: UUID = req.context.user_id

            with self.db_session() as db:
                recipes = db.scalars(select(Recipe)
                                     .where(Recipe.author_id == user_id)
                                     .order_by(Recipe.rating.desc(), Recipe.date_created.asc())
                                     .offset((page - 1) * elements)
                                     .limit(elements)).all()

                res_data = []
                for recipe in recipes:
                    bookmark_record = db.scalar(select(BookmarkedRecipe).where((BookmarkedRecipe.recipe_id == recipe.id) & (BookmarkedRecipe.user_id == user_id)))
                    rating_record = db.scalar(select(RatedRecipe).where((RatedRecipe.recipe_id == recipe.id) & (RatedRecipe.user_id == user_id)))

                    data = RecipeData(
                        recipe,
                        bookmark_record is not None,
                        rating_record.score if rating_record is not None else None
                    )

                    res_data.append(data)

                query = select(func.count()).select_from(Recipe).where(Recipe.author_id == user_id)
                total_records: int = db.scalar(query)

                resp.media = serialize(GenericResponse(value={
                    'totalPages': math.ceil(total_records / elements),
                    'data': res_data
                }))
                resp.status = falcon.HTTP_200             
            
        except Exception as e:
            resp.media = serialize(ERROR_RESPONSE)
            resp.status = falcon.HTTP_500
            logging.exception(e)