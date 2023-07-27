FROM alpine:3.17

COPY requirements.txt .

RUN mkdir -p /var/www/recipe-platform && \
    mkdir -p /var/www/recipe-platform/data && \
    apk update && \
    apk add 'python3>=3.11.3' 'py3-pip<23.1' && \
    pip3 install -r ./requirements.txt && \
    rm ./requirements.txt

COPY ./recipe/recipe /var/www/recipe-platform/recipe
COPY ./recipe/alembic /var/www/recipe-platform/alembic
COPY ./recipe/alembic /var/www/recipe-platform/alembic.ini

WORKDIR /var/www/recipe-platform

CMD [ "gunicorn", "-b", "0.0.0.0:3000", "recipe.app:app" ]
