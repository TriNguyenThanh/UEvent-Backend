# Django Project Instructions

## Project Context

This is a Django REST API backend for UEvents - an event management system with the following apps:
- **events**: Event creation and management
- **users**: User authentication and profiles
- **locations**: Venue and location management
- **interactions**: User interactions (likes, comments, RSVPs)
- **registrations**: Event registration handling
- **notifications**: Notification system
- **moderation**: Content moderation
- **support**: Support and help system

## Django Coding Standards

### Models
- Always define `__str__()` method for better admin representation
- Use `verbose_name` and `verbose_name_plural` in Meta class
- Order fields logically: required fields first, then optional, then timestamps
- Add `related_name` to ForeignKey and ManyToMany fields (use `app_entity_set` format)
- Use `blank=True, null=True` appropriately (blank for forms, null for database)
- Always add indexes for frequently queried fields
- Use `get_absolute_url()` for models that have a detail view

Example:
```python
class Event(models.Model):
    title = models.CharField(max_length=200)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='events_organized')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        verbose_name = "Event"
        verbose_name_plural = "Events"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
```

### Serializers (DRF)
- Keep serializers in `serializers.py` within each app
- Use `ModelSerializer` when possible
- Define `fields` explicitly (avoid `'__all__'` in production)
- Add validation methods as `validate_<field_name>()`
- Use `SerializerMethodField` for computed fields
- Nest serializers for related objects when needed

### ViewSets and Views
- Use ViewSets for CRUD operations
- Use APIView for custom endpoints
- Always add permission classes
- Use filtering, searching, and pagination
- Add proper docstrings for auto-generated API docs
- Handle exceptions with appropriate HTTP status codes

### URLs
- Keep URL patterns in `urls.py` within each app
- Use `app_name` for namespacing
- Use descriptive URL names
- Include app URLs in main `core/urls.py`

### Migrations
- Review generated migrations before applying
- Use descriptive names for data migrations
- Never edit applied migrations
- Use `RunPython` for data migrations with reverse function

### Testing
- Write tests in `tests/` directory within each app
- Use `APITestCase` for API endpoints
- Test all CRUD operations
- Test permissions and authentication
- Use factories or fixtures for test data
- Aim for >80% code coverage

### Security
- Never commit secrets (use environment variables)
- Always validate and sanitize user input
- Use Django's built-in protections (CSRF, SQL injection, XSS)
- Implement proper authentication and permissions
- Use HTTPS in production
- Keep dependencies updated

### Code Organization
- One app per domain concept
- Keep views, serializers, models, and tests separate
- Use `common/` for shared utilities
- Keep business logic in models or services, not views
- Use signals sparingly (prefer explicit calls)

### Performance
- Use `select_related()` for ForeignKey relationships
- Use `prefetch_related()` for ManyToMany and reverse ForeignKey
- Add database indexes for frequently filtered/ordered fields
- Use pagination for list endpoints
- Cache expensive queries when appropriate
- Use database-level constraints when possible

## API Design Principles

- Follow RESTful conventions
- Use plural nouns for collections (`/events/`, not `/event/`)
- Version your API (`/api/v1/`)
- Return appropriate HTTP status codes
- Provide meaningful error messages
- Include pagination metadata in list responses
- Use hypermedia links when appropriate

## Documentation

- Add docstrings to all classes and complex functions
- Keep README.md updated with setup instructions
- Document API endpoints (use drf-spectacular or similar)
- Comment complex business logic
- Update PROJECT_STRUCTURE.md when adding new apps
