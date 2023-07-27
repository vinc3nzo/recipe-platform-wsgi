import falcon

from .resources.user import UserResource
from .resources.recipe import RecipeResource
from .resources.auth import AuthResource
from .resources.bookmark import BookmarkResource
from .resources.rating import RatingResource
from .resources.image import ImageResource, ImageStore

from .database.database import new_engine, new_sessionmaker
from .database.models import ImageConfig

from .util import (
    handle_fields_missing, FieldsMissing, handle_unauthorized, Unauthorized,
    handle_pagination_error, PaginationError, AccessDenied, handle_access_denied
)
from .security import get_admin_token

from .log import logging

import os
from dotenv import load_dotenv

def create_app(db_url: str) -> falcon.asgi.App:

    if os.environ.get('APP_SECRET') is None:
        raise Exception('Please, set the `APP_SECRET` environment variable. You may use the `.env` file for your convenience.')

    # Database initialization
    engine = new_engine(db_url)
    db_session = new_sessionmaker(engine)

    # Rest API Resources

    user_resource = UserResource(db_session)
    recipe_resource = RecipeResource(db_session)
    auth_resource = AuthResource(db_session)
    bookmark_resource = BookmarkResource(db_session)
    rating_resource = RatingResource(db_session)

    image_config = ImageConfig()
    image_store = ImageStore(db_session, image_config)
    image_resource = ImageResource(image_config, image_store)

    # Create Falcon application

    app = falcon.App()

    app.add_error_handler(FieldsMissing, handle_fields_missing)
    app.add_error_handler(Unauthorized, handle_unauthorized)
    app.add_error_handler(PaginationError, handle_pagination_error)
    app.add_error_handler(AccessDenied, handle_access_denied)

    app.add_route('/user', user_resource) # GET
    app.add_route('/user/{_id:uuid}', user_resource, suffix='by_id') # GET

    app.add_route('/recipe', recipe_resource) # GET, POST
    app.add_route('/recipe/{_id:uuid}', recipe_resource, suffix='by_id') # GET, PATCH[MODERATOR, ADMIN]
    app.add_route('/recipe/search', recipe_resource, suffix='by_tags') # GET
    app.add_route('/recipe/my', recipe_resource, suffix='my') # GET
    app.add_route('/recipe/pending', recipe_resource, suffix='pending') # GET[MODERATOR, ADMIN]
    app.add_route('/recipe/deined', recipe_resource, suffix='denied') # GET[MODERATOR, ADMIN]

    app.add_route('/recipe/{_id:uuid}/rating', rating_resource) # GET, POST
    app.add_route('/recipe/{_id:uuid}/bookmark', bookmark_resource, suffix='bookmark') # POST, DELETE

    app.add_route('/recipe/{recipe_id:uuid}/image', image_resource) # GET, POST
    app.add_route('/recipe/{recipe_id:uuid}/image/{image_id:uuid}', image_resource, suffix='image') # GET

    app.add_route('/bookmark', bookmark_resource) # GET, POST, DELETE

    app.add_route('/auth/login', auth_resource, suffix='login') # POST
    app.add_route('/auth/register', auth_resource, suffix='register') # POST

    return app

load_dotenv()

logging.debug('Virtual admin user for this session:')
logging.debug(get_admin_token())
logging.debug('Please, note that this is not a real database user, and it is only a signed JWT for the user with max priveleges.')

app = create_app('postgresql+psycopg2://postgres:1234@localhost:5432/recipe-wsgi')

from .spec import api
api.register(app)