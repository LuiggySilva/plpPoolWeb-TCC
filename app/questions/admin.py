from django.contrib import admin

from .models import Period


admin.site.register(Period, list_display=['name',], ordering=['-name'])
