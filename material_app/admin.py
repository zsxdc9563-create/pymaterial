from django.contrib import admin
from .models import MaterialOverview, ItemList, TransactionLog

admin.site.register(MaterialOverview)
admin.site.register(ItemList)
admin.site.register(TransactionLog)
