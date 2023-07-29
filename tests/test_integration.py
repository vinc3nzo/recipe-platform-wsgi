import pytest
import falcon
from falcon.testing import TestClient

from uuid import uuid4

from recipe.app import create_app
from recipe.security import get_admin_token

@pytest.fixture
def client() -> TestClient:
    return TestClient(
        create_app('sqlite:///db/test.db')
    )

def test_registration(client: TestClient):
    resp = client.simulate_post(
        '/auth/register',
        json={
            'username': 'minecrafter_2008',
            'password': '1234',
            'first_name': 'Regular',
            'last_name': 'User'
        }
    )

    assert resp.status_code == 201
    assert resp.json['errors'] == None

def test_login(client: TestClient):
    resp = client.simulate_post(
        '/auth/login',
        json={
            'username': 'minecrafter_2008',
            'password': '1234'
        }
    )

    assert resp.status_code == 200
    assert resp.json['errors'] == None
    assert 'token' in resp.json['value']

    # save the token
    pytest.user_token = resp.json['value']['token']

def test_get_my_profile(client: TestClient):
    # save the user id for use in other tests
    resp = client.simulate_get(
        '/user/my',
        headers={
            'Authorization': 'Bearer ' + pytest.user_token
        }
    )

    print(resp.json)

    assert resp.status_code == 200
    assert resp.json['errors'] == None
    assert 'id' in resp.json['value']

    pytest.user_id: str = resp.json['value']['id']

def test_list_users(client: TestClient):
    resp = client.simulate_get(
        '/user', # query parameters default to ?page=1&elements=20
        headers={
            'Authorization': 'Bearer ' + pytest.user_token
        }
    )

    assert resp.status_code == 200
    assert resp.json['errors'] == None
    assert 'totalPages' in resp.json['value']
    assert 'data' in resp.json['value']
    assert resp.json['value']['data'][0]['username'] == 'minecrafter_2008'

def test_unauthenticated_access(client: TestClient):
    resp = client.simulate_get(
        '/user' # query parameters default to ?page=1&elements=20
    )

    assert resp.status_code == 401
    assert resp.json['errors'] != None

def test_unauthorized_access(client: TestClient):
    # as a User, try to make someone a Moderator
    resp = client.simulate_patch(
        f'/user/{pytest.user_id}', # query parameters default to ?page=1&elements=20
        headers={
            'Authorization': 'Bearer ' + pytest.user_token
        }
    )

    assert resp.status_code == 403
    assert resp.json['errors'] != None

def test_add_new_recipes(client: TestClient):
    resp = client.simulate_post(
        '/recipe',
        json={
            'source':
"""
# Торт тирамису

## Ингредиенты
- ...
"""
        },
        headers={
            'Authorization': 'Bearer ' + pytest.user_token
        }
    )

    assert resp.status_code == 201
    assert resp.json['errors'] == None

    resp = client.simulate_post(
        '/recipe',
        json={
            'source':
"""
# Что-то еще

## Markdown - гениальная вещь
"""
        },
        headers={
            'Authorization': 'Bearer ' + pytest.user_token
        }
    )

    assert resp.status_code == 201
    assert resp.json['errors'] == None

    resp = client.simulate_get(
        '/recipe', # query parameters default to ?page=1&elements=20
        headers={
            'Authorization': 'Bearer ' + pytest.user_token
        }
    )

    assert resp.status_code == 200
    assert resp.json['errors'] == None
    assert len(resp.json['value']['data']) == 0 # recipes are not yet approved

    resp = client.simulate_get(
        '/recipe/my', # query parameters default to ?page=1&elements=20
        headers={
            'Authorization': 'Bearer ' + pytest.user_token
        }
    )

    assert resp.status_code == 200
    assert resp.json['errors'] == None
    assert len(resp.json['value']['data']) == 2

    # the user can view their own recipes, even if they
    # haven't been approved yet

    # save the recipe's ID for future reference
    pytest.recipe_id = resp.json['value']['data'][0]['id']

def test_self_approve_recipe(client: TestClient):
    # as a user, try to approve your own recipe
    resp = client.simulate_patch(
        f'/recipe/{pytest.recipe_id}',
        json={
            'status': 2
        },
        headers={
            'Authorization': 'Bearer ' + pytest.user_token
        }
    )

    assert resp.status_code == 403
    assert resp.json['errors'] != None

def test_empty_username(client: TestClient):
    # try to register a user with empty username
    resp = client.simulate_post(
        '/auth/register',
        json={
            'username': '',
            'password': '123456',
            'first_name': 'Spectree Will',
            'last_name': 'Catch It'
        },
        headers={
            'Authorization': 'Bearer ' + pytest.user_token
        }
    )

    assert resp.status_code == 422

def test_moderator_approve_recipe(client: TestClient):
    # Use the JWT of the superuser to approve a recipe.
    # It can also be used to make someone a Moderator
    # and let them approve or deny new recipes.
    superuser_token = get_admin_token()
    
    # approve the recipe
    resp = client.simulate_patch(
        f'/recipe/{pytest.recipe_id}',
        json={
            'status': 2 # Status.APPROVED
        },
        headers={
            'Authorization': 'Bearer ' + superuser_token
        }
    )

    assert resp.status_code == 200
    assert resp.json['errors'] == None
    assert resp.json['value']['status'] == 2

def test_bookmark_recipe(client: TestClient):
    # create another user
    resp = client.simulate_post(
        '/auth/register',
        json={
            'username': 'regular_user',
            'password': 'i_need_your_password',
            'first_name': 'Regular',
            'last_name': 'User'
        }
    )

    assert resp.status_code == 201
    assert resp.json['errors'] == None

    resp = client.simulate_post(
        '/auth/login',
        json={
            'username': 'regular_user',
            'password': 'i_need_your_password'
        }
    )

    assert resp.status_code == 200
    assert resp.json['errors'] == None

    new_user_token = resp.json['value']['token']

    # Let's bookmark one of the other user's recipes.

    # This recipe has been approved in the previous
    # test case.
    resp = client.simulate_post(
        f'/recipe/{pytest.recipe_id}/bookmark',
        headers={
            'Authorization': 'Bearer ' + new_user_token
        }
    )

    assert resp.status_code == 201
    assert resp.json['errors'] == None

    # try to add the same recipe once again
    resp = client.simulate_post(
        f'/recipe/{pytest.recipe_id}/bookmark',
        headers={
            'Authorization': 'Bearer ' + new_user_token
        }
    )

    assert resp.status_code == 200
    assert resp.json['errors'] != None

    # now list all bookmarks
    resp = client.simulate_get(
        '/bookmark', # query parameters default to ?page=1&elements=20
        headers={
            'Authorization': 'Bearer ' + new_user_token
        }
    )

    assert resp.status_code == 200
    assert resp.json['errors'] == None
    assert len(resp.json['value']['data']) == 1

    # and delete the bookmark
    resp = client.simulate_delete(
        f'/recipe/{pytest.recipe_id}/bookmark',
        headers={
            'Authorization': 'Bearer ' + new_user_token
        }   
    )

    assert resp.status_code == 200
    assert resp.json['errors'] == None

def test_rate_recipe(client: TestClient):
    # get the recipe's rating
    resp = client.simulate_get(
        f'/recipe/{pytest.recipe_id}/rating',
        headers={
            'Authorization': 'Bearer ' + pytest.user_token
        }
    )

    assert resp.status_code == 200
    assert resp.json['errors'] == None

    # currently, no-one has rated this recipe
    assert resp.json['value']['rating'] == 0

    # Rate the recipe

    # First, try to send the value that is not in [1; 5] range
    resp = client.simulate_post(
        f'/recipe/{pytest.recipe_id}/rating',
        json={
            'score': 10
        },
        headers={
            'Authorization': 'Bearer ' + pytest.user_token
        }
    )

    assert resp.status_code == 422
    
    # Now send a valid user score
    resp = client.simulate_post(
        f'/recipe/{pytest.recipe_id}/rating',
        json={
            'score': 4
        },
        headers={
            'Authorization': 'Bearer ' + pytest.user_token
        }
    )

    assert resp.status_code == 201
    assert resp.json['errors'] == None

    # the score can be seen by anyone
    resp = client.simulate_post(
        '/auth/login',
        json={
            'username': 'regular_user',
            'password': 'i_need_your_password'
        }
    )

    assert resp.status_code == 200

    other_user_token = resp.json['value']['token']

    resp = client.simulate_get(
        f'/recipe/{pytest.recipe_id}',
        headers={
            'Authorization': 'Bearer ' + other_user_token
        }
    )

    assert resp.status_code == 200
    assert resp.json['errors'] == None

    # this user haven't rated this recipe
    assert resp.json['value']['user_score'] == None
    # but someone else has done it and now it is rated
    assert resp.json['value']['rating'] == 4

    # now this user has rated this recipe too
    resp = client.simulate_post(
        f'/recipe/{pytest.recipe_id}/rating',
        json={
            'score': 5
        },
        headers={
            'Authorization': 'Bearer ' + other_user_token
        }
    )

    assert resp.status_code == 201
    assert resp.json['errors'] == None
    
    resp = client.simulate_get(
        f'/recipe/{pytest.recipe_id}',
        headers={
            'Authorization': 'Bearer ' + other_user_token
        }
    )

    assert resp.status_code == 200
    assert resp.json['errors'] == None
    assert resp.json['value']['user_score'] == 5
    assert resp.json['value']['rating'] == (4 + 5) / 2

    # Someone may change their mind and re-rate the recipe.
    # This will cause the total rating to be calculated again.

    resp = client.simulate_post(
        f'/recipe/{pytest.recipe_id}/rating',
        json={
            'score': 3
        },
        headers={
            'Authorization': 'Bearer ' + pytest.user_token
        }
    )

    assert resp.status_code == 201
    assert resp.json['errors'] == None

    resp = client.simulate_get(
        f'/recipe/{pytest.recipe_id}',
        headers={
            'Authorization': 'Bearer ' + pytest.user_token
        }
    )

    assert resp.status_code == 200
    assert resp.json['errors'] == None
    assert resp.json['value']['user_score'] == 3
    assert resp.json['value']['rating'] == (3 + 5) / 2