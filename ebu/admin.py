from django.contrib import admin
from .models import Province, Kabupaten, User, Link, Alignment


admin.site.register(Province)
admin.site.register(Kabupaten)
admin.site.register(User)
admin.site.register(Link)

from django.contrib import admin
from leaflet.admin import LeafletGeoAdmin
from .models import Alignment

@admin.register(Alignment)
class AlignmentAdmin(LeafletGeoAdmin):
    settings_overrides = {
        'DEFAULT_CENTER': (-2.5489, 118.0149),  # Indonesia
        'DEFAULT_ZOOM': 5,
    }
