# Docker

# Ручная установка
> Требуется Python 3.11.3 или новее, с установленным pip.

Клонируйте репозиторий и перейдите в корневую папку.
```bash
git clone git@github.com:vinc3nzo/petboards.git
cd petboards
```

Создайте и активируйте виртуальную среду Python:
- GNU/Linux
```bash
cd petboards
python3 -m venv .venv
source ./.venv/bin/activate
```
- Windows (PowerShell)
```powershell
cd petboards
python -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\activate.ps1
```

Установите зависимости:
- GNU/Linux
```bash
pip3 install -r ../requirements.txt
```
- Windows (PowerShell)
```powershell
pip install -r ..\requirements.txt
```

Запустите `gunicorn` сервер:
- GNU/Linux
```bash
PETBOARDS_SECRET=super_secret gunicorn 'petboards.start:app'
```
- Windows (PowerShell)
```powershell
$env:PETBOARDS_SECRET = 'super_secret'; gunicorn 'petboards.start:app'
```

Сервер принимает запросы на порте `8000`.

# Docker образ
Существует [Docker образ](https://hub.docker.com/repository/docker/mangasaryanep/petboards/general) данного приложения. Чтобы им воспользоваться,
нужно его сначала загрузить:
```bash
docker pull mangasaryanep/petboards:1.0
```

Затем образ можно запустить в контейнере с помощью
```bash
docker run -e PETBOARDS_SECRET=super_secret -v 'petboards_data:/opt/petboards/data' -p 8000:8000 -d petboards:1.0
```

Приложение будет принимать запросы на порте `8000`.

В production-среде настоятельно рекомендуется установить другой `PETBOARDS_SECRET`,
так как значение этой переменной окружения используется при создании и проверке
Java Web Token, и ненадежный секрет может поставить под угрозу безопасность приложения.

# Petboards REST API 1.0

# Примеры объектов

## Пользователь

```json
{
  "user_id": "c2f4e98d-4a4c-4f4e-9a02-33c1b7ae8a0a",
  "username": "testuser",
  "first_name": "Test",
  "last_name": "User",
  "registered": 1631179416.965373,
  "last_login": 1631179416.965373,
  "boards": [
    {
      "board_id": "e0b4d4e4-1e0e-4c6e-8c1f-6a7cb6e4a6c7",
      "topic": "test board",
      "created_at": 1631179416.965373,
      "created_by": {
        "user_id": "c2f4e98d-4a4c-4f4e-9a02-33c1b7ae8a0a",
        "username": "testuser",
        "first_name": "Test",
        "last_name": "User",
        "registered": 1631179416.965373,
        "last_login": 1631179416.965373
      },
      "first_message": {
        "message_id": "4ad1b9fd-6620-4e8d-81c7-f6ae4c6e7b8a",
        "text": "test message",
        "author_id": "c2f4e98d-4a4c-4f4e-9a02-33c1b7ae8a0a",
        "timestamp": 1631179416.965373,
        "last_edited": null
      }
    }
  ]
}
```

## Сообщение

```json
{
  "message_id": "4ad1b9fd-6620-4e8d-81c7-f6ae4c6e7b8a",
  "text": "test message",
  "author_id": "c2f4e98d-4a4c-4f4e-9a02-33c1b7ae8a0a",
  "board_id": "e0b4d4e4-1e0e-4c6e-8c1f-6a7cb6e4a6c7",
  "timestamp": 1631179416.965373,
  "last_edited": null
}
```

## Доска с сообщениями

```json
{
  "board_id": "e0b4d4e4-1e0e-4c6e-8c1f-6a7cb6e4a6c7",
  "topic": "test board",
  "created_at": 1631179416.965373,
  "created_by": {
    "user_id": "c2f4e98d-4a4c-4f4e-9a02-33c1b7ae8a0a",
    "username": "testuser",
    "first_name": "Test",
    "last_name": "User",
    "registered": 1631179416.965373,
    "last_login": 1631179416.965373
  },
  "first_message": {
    "message_id": "4ad1b9fd-6620-4e8d-81c7-f6ae4c6e7b8a",
    "text": "test message",
    "author_id": "c2f4e98d-4a4c-4f4e-9a02-33c1b7ae8a0a",
    "timestamp": 1631179416.965373,
    "last_edited": null
  }
}
```

# API Endpoints

## Аутентификация (Authentication)

### \[POST\] `/auth/login`

Аутентифицирует пользователя по предоставленным имени пользователя и паролю и, в случае успешной аутентификации, возвращает JWT токен.

### Request Body

- `username`: имя зарегистрированного пользователя;
- `password`: пароль зарегистрированного пользователя.

### Response

- `200 OK`: возвращает JSON-объект с единственным полем `token`, который содержит созданный JWT токен пользователя.

### \[POST\] `/auth/register`

Регистрирует нового пользователя

### Request Body

- `username`: имя пользователя;
- `password`: пароль;
- `first_name`: имя;
- `last_name`: фамилия.

### Response

- `201 Created`: пустой ответ.
- `200 OK`: если имя пользователя уже занято.

## Доски (Message Boards)

### \[GET\] `/boards`

Возвращает список всех досок с сообщениями (с пагинацией).

### Request Body

- `token` JWT токен пользователя.

### Parameters

- `page`: индекс страницы;
- `elements`: число элементов на страницу (max: 30).

### Response

- `200 OK`: возвращает пагинированный список параметров.

### \[GET\] `/boards/{board_id}`

Возвращает конкретную доску с сообщениями.

### Request Body

- `token` JWT токен пользователя.

### Parameters

- `board_id`: UUID доски, которую требуется вернуть в ответе.

### Response

- `200 OK`: возвращает JSON объект, отражающий текущее состояние доски.

### \[POST\] `/boards`

Создает новую доску.

### Request Body

- `token`: JWT токен пользователя;
- `topic`: тема доски.

### Response

- `201 Created`: ответ содержит пустой объект и заголовок `Location` указывает на созданную доску.

## Сообщения (Messages)

### \[GET\] `/boards/{board_id}/messages`

Возвращает пагинированный список сообщений с конкретной доски.

### Request Body

- `token`: JWT токен пользователя;

### Parameters

- `board_id`: UUID доски, с которой требуется получить сообщения;
- `page`: индекс страницы для пагинации;
- `elements`: число элементов на страницу (max: 50).

### Response

- `200 OK`: возвращает пагинированный список объектов, представляющих собой сообщения.

### \[GET\] `/boards/{board_id}/messages/{message_id}`

Возвращает конкретное сообщение с конкретной доски.

### Request Body

- `token`: JWT токен пользователя;

### Parameters

- `board_id`: UUID доски, содержащей сообщение;
- `message_id`: UUID сообщения, которое требуется извлечь.

### Response

- `200 OK`: JSON объект, представляющий собой сообщение.

### \[POST\] `/boards/{board_id}/messages`

Создать новое сообщение на доске.

### Request Body

- `token`: JWT токен пользователя;
- `text`: текст сообщения.

### Response

- `201 Created`: пустой ответ с заголовком `Location` указывающим на вновь созданное сообщение.

### \[PATCH\] `/boards/{board_id}/messages/{message_id}`

Изменить конкретное сообщение на доске (пользователь может изменить только свое сообщение).

### Parameters

- `board_id`: UUID доски, содержащей сообщение;
- `message_id`: UUID сообщения, которое требуется изменить.

### Request Body

- `token`: JWT токен пользователя;
- `text`: новый текст сообщения.

### Response

- `200 OK`: JSON объект, представляющий измененное сообщение.

### \[DELETE\] `/boards/{board_id}/messages/{message_id}`

Удаляет сообщение с доски (пользователь может удалить только свое сообщение).

### Parameters

- `board_id`: UUID доски, содержащей сообщение;
- `message_id`: UUID сообщения, которое требуется удалить.

### Request Body

- `token`: JWT токен пользователя.

### Response

- `200 OK`: пустой JSON объект.

## Пользователь (User)

### \[GET\] `/users`

Возвращает пагинированный список пользователей.

### Request Body

- `token`: JWT токен пользователя.

### Parameters

- `page`: номер страницы для пагинации;
- `elements`: количество элементов на страницу (max: 30).

### Response

- `200 OK`: пагинированный список объектов, представляющих пользователей.

### \[GET\] `/users/{user_id}`

Возвращает одного конкретного пользователя.

### Request Body

- `token`: JWT токен пользователя (того, кто делает запрос).

### Parameters

- `user_id`: UUID пользователя, представление которого требуется получить.

### Response

- `200 OK`: JSON объект, представляющий конкретного пользователя.
