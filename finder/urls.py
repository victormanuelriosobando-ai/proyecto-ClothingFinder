from django.urls import path, register_converter

from . import views


class ModuloConverter:
    """Solo acepta los módulos que tienen CRUD (tiendas, productos, resenas, reportes)."""
    regex = '|'.join(views.CRUD)

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(ModuloConverter, 'modulo')

urlpatterns = [
    # Sitio público
    path('', views.landing, name='landing'),
    path('tienda/<int:pk>/', views.detalle_tienda, name='detalle_tienda'),
    path('reporte/nuevo/', views.crear_reporte, name='crear_reporte'),

    # Autenticación y panel
    path('registro/', views.signup, name='registro'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('panel/', views.panel, name='panel'),

    # CRUD: /tiendas/, /tiendas/nuevo/, /tiendas/3/, /tiendas/3/editar/, /tiendas/3/eliminar/
    path('<modulo:slug>/', views.lista, name='lista'),
    path('<modulo:slug>/nuevo/', views.crear, name='crear'),
    path('<modulo:slug>/<int:pk>/', views.detalle, name='detalle'),
    path('<modulo:slug>/<int:pk>/editar/', views.editar, name='editar'),
    path('<modulo:slug>/<int:pk>/eliminar/', views.eliminar, name='eliminar'),
]
