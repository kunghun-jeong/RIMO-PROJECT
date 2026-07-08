from django.contrib import admin
from .models import NaturalIntent, NetworkIntent, ApplicationIntent, PolicyIntent

admin.site.register(NaturalIntent)
admin.site.register(NetworkIntent)
admin.site.register(ApplicationIntent)
admin.site.register(PolicyIntent)