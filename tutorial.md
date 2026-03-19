# Tổng quan flow chuẩn

```text
Init project
→ Setup structure
→ Implement feature (model → service → API)
→ Write unit test
→ Dockerize
→ Setup CI (test + lint)
→ Setup CD (deploy staging → production)
```

---

# 1. INIT PROJECT (chuẩn production)


```bash
python -m venv venv
source venv/bin/activate

pip install django djangorestframework psycopg2-binary python-dotenv

django-admin startproject config .
mkdir apps common
```

---

# 2. STRUCTURE CHUẨN (production-ready)

```bash
project/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── apps/
│   ├── users/
│   ├── products/
│
├── common/
│   ├── permissions.py
│   ├── exceptions.py
│   └── utils.py
│
├── tests/
├── docker/
├── .env
├── manage.py
├── requirements.txt
└── docker-compose.yml
```

---

# 3. SETTINGS (tách môi trường)

## `config/settings/base.py`

```python
INSTALLED_APPS = [
    'rest_framework',
    'apps.users',
    'apps.products',
]
```

---

## `dev.py`

```python
from .base import *

DEBUG = True
```

---

## `prod.py`

```python
from .base import *

DEBUG = False
ALLOWED_HOSTS = ['your-domain.com']
```

---

## Run server đúng cách

```bash
export DJANGO_SETTINGS_MODULE=config.settings.dev
python manage.py runserver
```

---

# 4. CREATE APP (feature-based)

```bash
python manage.py startapp products apps/products
```

---

# 5. IMPLEMENT FEATURE (chuẩn senior)

## structure trong app

```bash
products/
├── models.py
├── serializers.py
├── views.py
├── services.py       # ⭐ business logic
├── selectors.py      # ⭐ query
├── urls.py
├── tests/
```

---

## Naming convention (rất quan trọng)

| Type       | Naming            |
| ---------- | ----------------- |
| Model      | Product           |
| Serializer | ProductSerializer |
| Service    | create_product    |
| Selector   | get_product_by_id |
| View       | ProductViewSet    |

---

## Ví dụ flow chuẩn

### `services.py`

```python
def create_product(data):
    if data["price"] < 0:
        raise ValueError("Invalid price")

    return Product.objects.create(**data)
```

---

### `selectors.py`

```python
def get_products():
    return Product.objects.all()
```

---

### `views.py`

```python
class ProductViewSet(ModelViewSet):
    queryset = get_products()
    serializer_class = ProductSerializer
```

---

# 6. URL DESIGN (RESTful + versioning)

```python
# config/urls.py
urlpatterns = [
    path('api/v1/', include('apps.products.urls')),
]
```

---

```python
# products/urls.py
router = DefaultRouter()
router.register(r'products', ProductViewSet)

urlpatterns = router.urls
```

---

# 7. UNIT TEST (chuẩn production)

## CLI

```bash
python manage.py test
```

---

## Structure

```bash
products/tests/
├── test_models.py
├── test_services.py   # ⭐ quan trọng nhất
├── test_views.py
├── test_selectors.py
```

---

## Example test service

```python
class ProductServiceTest(TestCase):

    def test_create_product_success(self):
        data = {"name": "A", "price": 10}
        product = create_product(data)

        self.assertEqual(product.name, "A")

    def test_create_product_invalid(self):
        data = {"name": "A", "price": -1}

        with self.assertRaises(ValueError):
            create_product(data)
```

---

## Best practice

* test service > test view
* mỗi test = 1 case
* test cả happy path + error

---

# 8. DOCKERIZE

## `docker/Dockerfile`

```dockerfile
FROM python:3.11

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
```

---

## `docker-compose.yml`

```yaml
version: '3'

services:
  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
```

---

# 9. CI (GitHub Actions)

## `.github/workflows/ci.yml`

```yaml
name: Django CI

on: [push]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: 3.11

    - name: Install deps
      run: pip install -r requirements.txt

    - name: Run tests
      run: python manage.py test
```

---

# 10. CD (deploy)

## Flow

```text
push → CI pass → build docker image → push registry → deploy server
```

---

## Production command

```bash
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

---

# 11. Naming chuẩn (rất quan trọng)

## API

```bash
GET    /api/v1/products/
POST   /api/v1/products/
GET    /api/v1/products/{id}/
```

---

## Function

```python
create_product()
update_product()
get_product_by_id()
```

---

## Test

```python
test_create_product_success
test_create_product_invalid_price
```

---

# 12. Checklist senior-level
- Tách settings env
- Service layer rõ ràng
- Query tách riêngs
- RESTful API
- Test coverage
- Docker ready
- CI/CD pipeline