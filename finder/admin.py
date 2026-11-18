from django.contrib import admin

from .models import Product, Report, Review, Store


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'ciudad', 'estilo', 'correo', 'activa')
    search_fields = ('nombre', 'ciudad', 'estilo')
    list_filter = ('ciudad', 'activa')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tienda', 'categoria', 'estilo', 'precio', 'unidades')
    search_fields = ('nombre', 'categoria', 'estilo')
    list_filter = ('categoria', 'estilo')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('tienda', 'nombre_publico', 'calificacion', 'visible', 'creada')
    list_filter = ('calificacion', 'visible')


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'tipo', 'motivo', 'estado', 'creado')
    list_filter = ('tipo', 'estado')
