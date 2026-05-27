---
name: django-api
description: Generate a complete Django REST API endpoint with serializer, viewset, permissions, tests, and URL routing for an existing model
inputs:
  - name: app_name
    description: The Django app name (e.g., events, users)
    required: true
  - name: model_name
    description: The existing model name (e.g., Event, Category)
    required: true
  - name: model_code
    description: Code or fields of the existing model. If not provided, you MUST analyze the existing `models.py` file or ask the user for the code.
    required: false
  - name: endpoint_type
    description: Type of endpoint - full CRUD, read-only, or custom action
    required: false
    default: "full"
  - name: permissions
    description: Permission requirements (e.g., authenticated, admin-only, public-read)
    required: false
    default: "authenticated"
---

# Generate Django REST API Endpoint

Create a complete REST API endpoint for the existing **{{model_name}}** model in the `apps/{{app_name}}` app.

**Endpoint Type:** {{endpoint_type}}
**Permissions:** {{permissions}}

## Requirements

**Crucial Context Step**: Before generating, ensure you know the exact schema of the {{model_name}} model. If `{{model_code}}` is empty, read the corresponding `models.py` file or ask the user. Do not hallucinate fields.

**Imports**: Ensure all necessary Django and DRF imports are included at the top of each file.

1. **Serializer** (`apps/{{app_name}}/serializers.py`):
   - Create or update `{{model_name}}Serializer` extending `ModelSerializer`
   - Include all relevant fields explicitly
   - Handle Relationships: Optimize handling of ForeignKey or ManyToMany fields (e.g., using `PrimaryKeyRelatedField` or nested serializers where appropriate).
   - Implement field-level validation methods
   - Add `create()` and `update()` methods if custom logic needed

2. **ViewSet** (`apps/{{app_name}}/views.py`):
   - Create `{{model_name}}ViewSet` based on endpoint_type:
     - `full`: Use `ModelViewSet` (all CRUD operations)
     - `read-only`: Use `ReadOnlyModelViewSet` (list and retrieve only)
     - `custom`: Use appropriate ViewSet with custom actions
   - Add queryset with proper filtering, and strictly optimize queries using `select_related` and `prefetch_related` to avoid N+1 issues.
   - Set serializer_class
   - Configure permission_classes based on permissions input
   - Add filtering backends (SearchFilter, OrderingFilter, DjangoFilterBackend)
   - Define `filterset_fields`, `search_fields`, `ordering_fields`
   - Add pagination_class if not default
   - Add comprehensive docstring for API documentation
   - Implement custom actions if needed (use `@action` decorator)

3. **Permissions** (if custom needed):
   - Create custom permission class in `apps/{{app_name}}/permissions.py` if needed
   - Map permission input to appropriate DRF permission classes:
     - `authenticated`: `IsAuthenticated`
     - `admin-only`: `IsAdminUser`
     - `public-read`: Custom permission allowing read for all, write for authenticated
     - `owner-only`: Custom `IsOwnerOrReadOnly` permission

4. **URL Routing** (`apps/{{app_name}}/urls.py`):
   - Register viewset with DefaultRouter
   - Use plural, lowercase URL prefix (e.g., `events`, `categories`)
   - Ensure app URLs are included in main `core/urls.py`

5. **Tests** (`apps/{{app_name}}/tests/test_api.py`):
   - Create test class extending `APITestCase`
   - Test all CRUD operations (based on endpoint_type)
   - Test permissions and authentication
   - Test filtering, searching, and pagination
   - Test validation and error responses
   - Use setUp() to create test data and authenticate

6. **API Documentation**:
   - Add docstrings to viewset and custom actions
   - Include example request/response in docstrings
   - Document query parameters

## Permission Mapping

```python
# authenticated
permission_classes = [IsAuthenticated]

# admin-only
permission_classes = [IsAdminUser]

# public-read (create custom permission)
permission_classes = [IsAuthenticatedOrReadOnly]

# owner-only (create custom permission)
permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
```

## Example Test Structure

```python
class {{model_name}}APITestCase(APITestCase):
    def setUp(self):
        # Create test user and authenticate
        # Create test data
        pass
    
    def test_list_{{model_name|lower}}s(self):
        # Test list endpoint
        pass
    
    def test_create_{{model_name|lower}}(self):
        # Test create endpoint
        pass
    
    def test_retrieve_{{model_name|lower}}(self):
        # Test detail endpoint
        pass
    
    def test_update_{{model_name|lower}}(self):
        # Test update endpoint
        pass
    
    def test_delete_{{model_name|lower}}(self):
        # Test delete endpoint
        pass
    
    def test_permissions(self):
        # Test permission restrictions
        pass
```

## Deliverables

After generation, provide:
1. All code files with complete implementation
2. Command to run tests: `python manage.py test apps.{{app_name}}.tests.test_api`
3. Example API requests using curl or httpie
4. Endpoint URLs (e.g., `/api/v1/events/`)
5. Next steps for integration
