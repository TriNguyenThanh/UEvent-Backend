import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.test import Client
from apps.users.models import User

client = Client()
user = User.objects.filter(is_superuser=True).first()
client.force_login(user)

response = client.get("/api/v1/admin/users/export/?export_format=xlsx")
print("Response status:", response.status_code)
print("Response header content-type:", response.get('Content-Type'))
print("Content-Disposition:", response.get('Content-Disposition'))
