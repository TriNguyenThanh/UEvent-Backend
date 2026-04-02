---
description: "Code review rules for Django REST Framework views and viewsets: validate permissions, queryset optimization, filtering configuration, and proper action definitions. Use when: reviewing or editing views or viewsets."
applyTo: '**/views.py', "**/apps/*/views/*.py", "**/viewsets.py"
---

# Django Views/ViewSets Code Review Rules

When reviewing or modifying DRF view files, ensure the following:

## ViewSet Configuration

### 1. Required Attributes
Every ViewSet MUST define:

```python
class EventViewSet(viewsets.ModelViewSet):
    """ViewSet for managing events."""
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]
```

### 2. Optimized Queryset
Always optimize querysets to avoid N+1 queries:

```python
# Good - optimized queryset
queryset = Event.objects.select_related(
    'organizer',
    'location'
).prefetch_related(
    'attendees',
    'categories'
)

# Bad - will cause N+1 queries
queryset = Event.objects.all()
```

### 3. Dynamic Serializer Selection
Use different serializers for different actions:

```python
def get_serializer_class(self):
    """Return appropriate serializer based on action."""
    if self.action == 'list':
        return EventListSerializer
    elif self.action in ['create', 'update', 'partial_update']:
        return EventWriteSerializer
    return EventDetailSerializer
```

## Permissions

### Permission Classes
Set appropriate permissions for the entire ViewSet:

```python
# Authenticated users only
permission_classes = [IsAuthenticated]

# Admin only
permission_classes = [IsAdminUser]

# Authenticated for write, anyone for read
permission_classes = [IsAuthenticatedOrReadOnly]

# Custom permissions
permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
```

### Action-Specific Permissions
Override for specific actions:

```python
def get_permissions(self):
    """Set permissions based on action."""
    if self.action in ['list', 'retrieve']:
        return [AllowAny()]
    elif self.action == 'destroy':
        return [IsAdminUser()]
    return [IsAuthenticated()]
```

## Filtering and Search

### Configure Filter Backends

```python
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend

class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # Exact match filtering
    filterset_fields = ['status', 'organizer', 'location']
    
    # Text search
    search_fields = ['title', 'description']
    
    # Ordering options
    ordering_fields = ['created_at', 'start_date', 'title']
    ordering = ['-created_at']  # Default ordering
```

### Custom Filter Queryset

```python
def get_queryset(self):
    """Filter queryset based on user and parameters."""
    queryset = super().get_queryset()
    user = self.request.user
    
    # Filter by query parameters
    status = self.request.query_params.get('status')
    if status:
        queryset = queryset.filter(status=status)
    
    # Filter based on user permissions
    if not user.is_staff:
        queryset = queryset.filter(status='published')
    
    return queryset
```

## Custom Actions

### Action Decorator
Use `@action` for custom endpoints:

```python
from rest_framework.decorators import action
from rest_framework.response import Response

class EventViewSet(viewsets.ModelViewSet):
    
    @action(detail=True, methods=['post'])
    def register(self, request, pk=None):
        """Register current user for this event."""
        event = self.get_object()
        user = request.user
        
        # Business logic
        registration, created = Registration.objects.get_or_create(
            event=event,
            user=user
        )
        
        if created:
            return Response({'status': 'registered'}, status=201)
        return Response({'status': 'already registered'}, status=200)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get list of upcoming events."""
        upcoming = self.get_queryset().filter(
            start_date__gte=timezone.now()
        ).order_by('start_date')
        
        page = self.paginate_queryset(upcoming)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)
```

## Pagination

### Set Pagination Class

```python
from rest_framework.pagination import PageNumberPagination

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class EventViewSet(viewsets.ModelViewSet):
    pagination_class = StandardResultsSetPagination
```

## Error Handling

### Proper Exception Handling

```python
from rest_framework.exceptions import ValidationError, NotFound, PermissionDenied

@action(detail=True, methods=['post'])
def cancel(self, request, pk=None):
    """Cancel an event."""
    event = self.get_object()
    
    # Check permissions
    if event.organizer != request.user:
        raise PermissionDenied("Only the organizer can cancel this event.")
    
    # Validate state
    if event.status == 'cancelled':
        raise ValidationError("Event is already cancelled.")
    
    # Perform action
    event.status = 'cancelled'
    event.save()
    
    serializer = self.get_serializer(event)
    return Response(serializer.data)
```

### HTTP Status Codes

Use appropriate status codes:

```python
from rest_framework import status

# 200 - Success
return Response(data, status=status.HTTP_200_OK)

# 201 - Created
return Response(data, status=status.HTTP_201_CREATED)

# 204 - No Content (for successful delete)
return Response(status=status.HTTP_204_NO_CONTENT)

# 400 - Bad Request
return Response(errors, status=status.HTTP_400_BAD_REQUEST)

# 404 - Not Found
raise NotFound("Event not found.")

# 403 - Forbidden
raise PermissionDenied("You don't have permission.")
```

## API Documentation

### Docstrings
Add comprehensive docstrings:

```python
class EventViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing events.
    
    Provides CRUD operations for events with the following features:
    - List and filter events by status, organizer, location
    - Search events by title and description
    - Register/unregister users for events
    - View upcoming events
    
    Permissions:
    - List/Retrieve: Any user
    - Create/Update: Authenticated users
    - Delete: Event organizer or admin
    """
    
    @action(detail=True, methods=['post'])
    def register(self, request, pk=None):
        """
        Register the current user for an event.
        
        Returns:
            201: User successfully registered
            200: User already registered
            400: Registration failed (event full, etc.)
            404: Event not found
        """
        pass
```

## Performance Best Practices

### 1. Select/Prefetch Related
Always optimize database queries:

```python
def get_queryset(self):
    queryset = Event.objects.all()
    
    # Optimize based on action
    if self.action == 'list':
        queryset = queryset.select_related('organizer')
    elif self.action == 'retrieve':
        queryset = queryset.select_related(
            'organizer',
            'location'
        ).prefetch_related(
            'attendees',
            'categories'
        )
    
    return queryset
```

### 2. Avoid Heavy Computation in Views
Move complex logic to models, managers, or services:

```python
# Bad - heavy computation in view
@action(detail=True)
def statistics(self, request, pk=None):
    event = self.get_object()
    stats = {
        'total': event.attendees.count(),
        'confirmed': event.attendees.filter(status='confirmed').count(),
        # ... more queries
    }
    return Response(stats)

# Good - use model method or manager
@action(detail=True)
def statistics(self, request, pk=None):
    event = self.get_object()
    stats = event.get_statistics()  # Optimized in model
    return Response(stats)
```

## Red Flags

❌ **Reject or flag these issues:**
- Hallucinated references to non-existent model fields, serializer fields, or methods (e.g., filtering or searching by fields that don't exist)
- Missing necessary Django or DRF imports
- ViewSet without permission_classes
- Missing queryset optimization (no select_related/prefetch_related)
- Using `.filter()` in loops (N+1 queries)
- Not paginating list endpoints
- Missing error handling
- Hardcoded URLs or paths
- Business logic in views instead of models/services
- Not using appropriate HTTP status codes
- Missing docstrings on custom actions
- Accessing `request.user` without checking `is_authenticated`

## Best Practices

✅ **Encourage:**
- Thin views - delegate to models/services
- Proper queryset optimization
- Consistent error handling
- Clear API documentation
- Using throttling for sensitive endpoints
- Logging important actions
- Transaction handling for multi-step operations
- Using ViewSet inheritance appropriately
- Testing all endpoints and edge cases

## Import Organization

```python
# Standard library
from datetime import datetime

# Django
from django.db import transaction
from django.utils import timezone

# Django REST Framework
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend

# Local
from .models import Event
from .serializers import EventSerializer, EventDetailSerializer
from .permissions import IsOwnerOrReadOnly
```

## Testing Checklist

Ensure views have tests for:
- [ ] All CRUD operations
- [ ] Custom actions
- [ ] Permission checks
- [ ] Filtering and search
- [ ] Pagination
- [ ] Error cases
- [ ] Edge cases
