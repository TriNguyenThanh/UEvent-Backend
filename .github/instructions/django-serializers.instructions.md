---
description: "Code review rules for Django REST Framework serializers: validate field definitions, ensure proper validation methods, check nested serializers. Use when: reviewing or editing serializer files."
applyTo: "**/serializers.py", "**/apps/*/serializers/*.py"
---

# Django Serializers Code Review Rules

When reviewing or modifying DRF serializer files, ensure the following:

## Required Elements

### 1. Explicit Field Definition
Always explicitly list fields in Meta class (never use `'__all__'` in production):

```python
class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['id', 'title', 'description', 'organizer', 'created_at']  # Good
        # fields = '__all__'  # Bad - avoid in production
```

### 2. Read-Only Fields
Mark fields that shouldn't be modified via API:

```python
class Meta:
    model = Event
    fields = ['id', 'title', 'created_at', 'updated_at']
    read_only_fields = ['id', 'created_at', 'updated_at']
```

## Validation

### Field-Level Validation
Use `validate_<field_name>()` for single field validation:

```python
def validate_end_date(self, value):
    """Ensure end date is in the future."""
    if value < timezone.now():
        raise serializers.ValidationError("End date must be in the future.")
    return value
```

### Object-Level Validation
Use `validate()` for multi-field validation:

```python
def validate(self, data):
    """Ensure end_date is after start_date."""
    if data.get('end_date') and data.get('start_date'):
        if data['end_date'] < data['start_date']:
            raise serializers.ValidationError({
                'end_date': "End date must be after start date."
            })
    return data
```

## Nested Serializers

### Read-Only Nested Objects
Use nested serializers for read operations:

```python
class EventDetailSerializer(serializers.ModelSerializer):
    organizer = UserSerializer(read_only=True)
    location = LocationSerializer(read_only=True)
    
    class Meta:
        model = Event
        fields = ['id', 'title', 'organizer', 'location']
```

### Write Operations
Use PrimaryKeyRelatedField or SlugRelatedField for write operations:

```python
class EventCreateSerializer(serializers.ModelSerializer):
    organizer_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='organizer',
        write_only=True
    )
    
    class Meta:
        model = Event
        fields = ['id', 'title', 'organizer_id']
```

## SerializerMethodField

Use for computed values that aren't model fields:

```python
class EventSerializer(serializers.ModelSerializer):
    attendee_count = serializers.SerializerMethodField()
    is_past = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = ['id', 'title', 'attendee_count', 'is_past']
    
    def get_attendee_count(self, obj):
        """Return count of registered attendees."""
        return obj.registrations.count()
    
    def get_is_past(self, obj):
        """Check if event has already ended."""
        return obj.end_date < timezone.now()
```

## Custom Create/Update

### Create Method
Override for custom creation logic:

```python
def create(self, validated_data):
    """Create event with current user as organizer."""
    request = self.context.get('request')
    validated_data['organizer'] = request.user
    return super().create(validated_data)
```

### Update Method
Override for custom update logic:

```python
def update(self, instance, validated_data):
    """Prevent changing organizer after creation."""
    validated_data.pop('organizer', None)  # Remove if present
    return super().update(instance, validated_data)
```

## Multiple Serializers Pattern

Use different serializers for different operations:

```python
# List view - minimal fields
class EventListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['id', 'title', 'start_date']

# Detail view - all fields with nested data
class EventDetailSerializer(serializers.ModelSerializer):
    organizer = UserSerializer(read_only=True)
    
    class Meta:
        model = Event
        fields = ['id', 'title', 'description', 'organizer', 'created_at']

# Create/Update - writable fields only
class EventWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['title', 'description', 'start_date', 'end_date']
```

Then in ViewSet:
```python
def get_serializer_class(self):
    if self.action == 'list':
        return EventListSerializer
    elif self.action in ['create', 'update', 'partial_update']:
        return EventWriteSerializer
    return EventDetailSerializer
```

## Context Usage

Access request context in serializers:

```python
class EventSerializer(serializers.ModelSerializer):
    can_edit = serializers.SerializerMethodField()
    
    def get_can_edit(self, obj):
        """Check if current user can edit this event."""
        request = self.context.get('request')
        if request and request.user:
            return obj.organizer == request.user
        return False
```

## Performance Optimization

### Select/Prefetch Related
Handle in ViewSet queryset, not serializer:
```python
# In ViewSet
def get_queryset(self):
    return Event.objects.select_related('organizer', 'location').prefetch_related('attendees')
```

### Avoid N+1 Queries
Use `SerializerMethodField` carefully:
```python
# Bad - causes N+1 queries
def get_attendee_names(self, obj):
    return [user.name for user in obj.attendees.all()]

# Good - use prefetch_related in ViewSet queryset
def get_attendee_names(self, obj):
    return [user.name for user in obj.attendees.all()]  # OK if prefetched
```

## Red Flags

❌ **Reject or flag these issues:**
- Hallucinated fields in `fields` list that do not exist on the model or aren't explicitly defined (like `SerializerMethodField`)
- Missing necessary Django or DRF imports
- Using `fields = '__all__'` in production code
- Missing validation for required business rules
- Nested writes without proper handling
- Not using `read_only=True` on computed fields
- Exposing sensitive fields (passwords, tokens)
- SerializerMethodField causing N+1 queries
- Not handling exceptions in create/update methods
- Using `many=True` without source validation

## Best Practices

✅ **Encourage:**
- Separate serializers for read/write operations
- Clear field documentation in docstrings
- Proper use of `source` and `write_only` parameters
- Validation that matches business rules
- Using `to_representation()` for response formatting
- Using `to_internal_value()` for input normalization
- Keeping serializers focused and single-purpose
- Testing serializers independently

## Import Organization

```python
# Standard library
from decimal import Decimal

# Django
from django.utils import timezone
from django.contrib.auth import get_user_model

# Django REST Framework
from rest_framework import serializers

# Local
from .models import Event
from apps.users.serializers import UserSerializer
```

## Documentation

Add docstrings to complex serializers:

```python
class EventSerializer(serializers.ModelSerializer):
    """
    Serializer for Event model.
    
    Used for list and detail views. Includes nested organizer data
    and computed fields for attendee count and event status.
    """
    
    def validate_capacity(self, value):
        """Ensure capacity is at least 1."""
        if value < 1:
            raise serializers.ValidationError("Capacity must be at least 1.")
        return value
```
