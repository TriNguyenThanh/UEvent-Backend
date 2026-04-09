---
name: django-model
description: Generate a Django model with all best practices including proper field types, Meta class, string representation, and optional related serializer and viewset
inputs:
  - name: app_name
    description: The Django app name where the model should be created (e.g., events, users)
    required: true
  - name: model_name
    description: The name of the model in singular form (e.g., Event, Category, Comment)
    required: true
  - name: fields
    description: Comma-separated list of fields with types (e.g., "title:char, description:text, price:decimal, date:datetime")
    required: true
  - name: related_models_context
    description: Context about related models (for ForeignKeys/ManyToMany). If left blank, you MUST review existing `models.py` files first.
    required: false
  - name: include_api
    description: Whether to include serializer and viewset (yes/no)
    required: false
    default: "yes"
---

# Generate Django Model

Create a complete Django model in the `apps/{{app_name}}` app with the following specifications:

**Model Name:** {{model_name}}
**Fields:** {{fields}}
**Include API Components:** {{include_api}}

## Requirements

**Crucial Context Step**: Before generating, ensure you review the existing `models.py` in the relevant app to prevent duplicating models, hallucinating related model names, or causing import conflicts.

**Imports**: Ensure all necessary Django and DRF imports are included at the top of each file.

1. **Model File** (`apps/{{app_name}}/models.py`):
   - Create the {{model_name}} model with specified fields
   - Add appropriate field types, max_lengths, and constraints
   - Include `created_at` and `updated_at` timestamp fields
   - Add `__str__()` method returning a meaningful representation
   - Define Meta class with:
     - `verbose_name` and `verbose_name_plural`
     - `ordering` (typically by `-created_at`)
     - Appropriate indexes on frequently queried fields
   - Add any necessary ForeignKey relationships with `related_name`

2. **Admin Registration** (`apps/{{app_name}}/admin.py`):
   - Register the model with Django admin
   - Add `list_display` for key fields
   - Add `list_filter` for categorical fields
   - Add `search_fields` for text fields
   - Add `readonly_fields` for timestamps

3. **If include_api is "yes"**, create:
   
   a. **Serializer** (`apps/{{app_name}}/serializers.py`):
      - Create a ModelSerializer for {{model_name}}
      - Explicitly list fields (don't use `__all__`)
      - Handle Relationships: Optimize handling of ForeignKey or ManyToMany fields
      - Add any custom validation methods
   
   b. **ViewSet** (`apps/{{app_name}}/views.py`):
      - Create a ModelViewSet for {{model_name}}
      - Add appropriate permission classes
      - Enable filtering, searching, and pagination
      - Strictly optimize queries using `select_related` and `prefetch_related` to avoid N+1 issues.
      - Add docstring for API documentation
   
   c. **URLs** (`apps/{{app_name}}/urls.py`):
      - Register the viewset with a router
      - Use appropriate URL prefix (plural form)

4. **Migration**:
   - Generate the migration file with: `python manage.py makemigrations {{app_name}}`
   - Show the migration command but don't apply it yet

## Field Type Mapping

Convert the field specifications to appropriate Django field types:
- `char` → `CharField(max_length=200)`
- `text` → `TextField()`
- `int` → `IntegerField()`
- `decimal` → `DecimalField(max_digits=10, decimal_places=2)`
- `bool` → `BooleanField(default=False)`
- `date` → `DateField()`
- `datetime` → `DateTimeField()`
- `email` → `EmailField()`
- `url` → `URLField()`
- `fk:ModelName` → `ForeignKey('ModelName', on_delete=models.CASCADE, related_name='...')`
- `m2m:ModelName` → `ManyToManyField('ModelName', related_name='...')`

## Example Output Structure

Show the complete code for each file with proper imports and formatting. After generating all files, provide:
- Summary of files created/modified
- Migration command to run
- URL to register in main `core/urls.py` if creating new API endpoints
- Next steps (e.g., apply migration, test endpoints)
