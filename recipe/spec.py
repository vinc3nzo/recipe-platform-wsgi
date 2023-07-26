from spectree import SpecTree, SecurityScheme

api = SpecTree(
    'falcon',
    title='Recipe Sharing Platform API',
    version='0.0.1',
    openapi_version='3.0.3',
    description='A backend application for writing recipes in Markdown, saving and rating them.',
    contact={'name': 'Evgeny', 'email': 'mangasaryan.ep@gmail.com', 'url': 'https://evgenym.com'},
    security_schemes=[
        SecurityScheme(
            name='auth_jwt',
            data={
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT'
            }
        )
    ],
    security={
        'auth_jwt': []
    }
)