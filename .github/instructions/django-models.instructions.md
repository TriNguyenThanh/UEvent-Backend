---
description: "Code review rules for Django models: enforce Meta class, string representation, indexes, and relationship naming conventions. Use when: reviewing or editing Django model files."
applyTo: "**/models.py", "**/apps/*/models/*.py"
---

# Django Models Code Review Rules

When reviewing or modifying Django model files, ensure the following:

## Required Elements

### 1. Meta Class
Every model MUST have a Meta class with:
- `verbose_name`: Human-readable singular name
- `verbose_name_plural`: Human-readable plural name  
- `ordering`: Default ordering (typically `['-created_at']` or `['name']`)

```python
class Meta:
    verbose_name = "Event"
    verbose_name_plural = "Events"
    ordering = ['-created_at']
```

### 2. String Representation
Every model MUST define `__str__()` returning a meaningful string:
```python
def __str__(self):
    return self.title  # or other identifying field
```

### 3. Timestamps
Most models should have timestamp fields:
```python
created_at = models.DateTimeField(auto_now_add=True, db_index=True)
updated_at = models.DateTimeField(auto_now=True)
```

## Field Guidelines

### Relationships
- **ForeignKey**: Always include `related_name` using format `{app}_{model}_set` or descriptive name
  ```python
  organizer = models.ForeignKey(
      User, 
      on_delete=models.CASCADE,
      related_name='events_organized'  # Good
  )
  ```

- **ManyToManyField**: Always include descriptive `related_name`
  ```python
  attendees = models.ManyToManyField(
      User,
      related_name='events_attending'
  )
  ```

### Null and Blank
- Use `null=True` for database NULL support (use with CharField/TextField carefully)
- Use `blank=True` for form validation (allows empty in forms)
- For CharField/TextField, prefer `blank=True` without `null=True` (store empty string, not NULL)

```python
# Good for text fields
description = models.TextField(blank=True, default='')

# Good for optional foreign keys
category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL)

# Good for optional dates
published_at = models.DateTimeField(null=True, blank=True)
```

### Indexes
Add `db_index=True` to fields that are:
- Frequently used in filters or lookups
- Used in ordering
- Foreign keys (automatically indexed, but verify)

```python
status = models.CharField(max_length=20, db_index=True)
created_at = models.DateTimeField(auto_now_add=True, db_index=True)
```

### Constraints
Use Meta constraints for complex validation:
```python
class Meta:
    constraints = [
        models.CheckConstraint(
            check=models.Q(end_date__gte=models.F('start_date')),
            name='end_date_after_start_date'
        ),
        models.UniqueConstraint(
            fields=['event', 'user'],
            name='unique_event_registration'
        )
    ]
```

## Field Ordering
Order fields logically within the model:
1. Primary identifiers (if custom)
2. Required fields
3. Optional fields
4. Relationships (ForeignKey, ManyToMany)
5. Metadata fields (status, flags)
6. Timestamps (created_at, updated_at)

## Methods and Properties

### Custom Methods
Place custom methods after `__str__()` but before Meta:
```python
def __str__(self):
    return self.title

def is_active(self):
    return self.status == 'active'

def get_absolute_url(self):
    return reverse('events:detail', kwargs={'pk': self.pk})

class Meta:
    ...
```

### Properties
Use `@property` for computed values:
```python
@property
def is_past(self):
    return self.end_date < timezone.now()
```

## Imports
Order imports in models.py:
1. Standard library
2. Django core
3. Third-party packages
4. Local imports

```python
from datetime import datetime

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

from common.models import BaseModel
```

## Red Flags

❌ **Reject or flag these issues:**
- Hallucinated fields or relations that don't exist in the actual project context
- Missing necessary Django standard imports
- Model without `__str__()` method
- Model without Meta class
- ForeignKey without `related_name`
- Use of `models.CharField(null=True)` (use `blank=True` instead)
- Missing `on_delete` in ForeignKey
- Circular imports between models
- Business logic in models that should be in services/managers
- Using `auto_now_add=True` with `default=` (redundant)

## Best Practices

✅ **Encourage:**
- Using custom managers for complex queries
- Abstracting common fields into base models
- Using validators for field-level validation
- Keeping models focused (single responsibility)
- Using `select_related()` and `prefetch_related()` in manager methods
- Adding helpful comments for complex business logic
- Using choices with `TextChoices` or `IntegerChoices`

```python
class EventStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    PUBLISHED = 'published', 'Published'
    CANCELLED = 'cancelled', 'Cancelled'

class Event(models.Model):
    status = models.CharField(
        max_length=20,
        choices=EventStatus.choices,
        default=EventStatus.DRAFT
    )
```
