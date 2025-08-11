from django.contrib import admin
from .models import Province, Kabupaten, User, Link
# Register your models here.
admin.site.register(Province)
admin.site.register(Kabupaten)
admin.site.register(User)
admin.site.register(Link)