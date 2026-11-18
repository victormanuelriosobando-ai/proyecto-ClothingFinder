# ClothingFinder con Django

Proyecto académico basado en la maquetación de ClothingFinder, conectado a Django.

## Instalación
```bash
python -m venv venv
venv\Scripts\activate          # Windows   (Linux/macOS: source venv/bin/activate)
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
Abre `http://127.0.0.1:8000/`. Las pruebas se ejecutan con `python manage.py test`.

## Módulos y CRUD
Cada módulo tiene **listar (con búsqueda y paginación), crear, ver, editar y eliminar** (con página de confirmación):

| Módulo    | Listar          | Crear                  |
|-----------|-----------------|------------------------|
| Usuarios  | `/usuarios/`    | `/usuarios/nuevo/`     |
| Tiendas   | `/tiendas/`     | `/tiendas/nuevo/`      |
| Productos | `/productos/`   | `/productos/nuevo/`    |
| Reseñas   | `/resenas/`     | `/resenas/nuevo/`      |
| Reportes  | `/reportes/`    | `/reportes/nuevo/`     |

Para cada registro: `/<modulo>/<id>/` (ver), `/<modulo>/<id>/editar/` y `/<modulo>/<id>/eliminar/`.
Todo el panel requiere iniciar sesión **con rol Administrador**. `/admin/` sigue disponible para administrar los modelos.

Los CRUD están definidos una sola vez en el diccionario `CRUD` de `finder/views.py`; para agregar un módulo nuevo basta con añadir una entrada allí y un menú en `base.html`.

## Usuarios y roles
Cada usuario tiene un perfil con **rol** (Cliente, Propietario de tienda o Administrador), teléfono y **estado** (Activo, Inactivo o Bloqueado).
- El registro público (`/registro/`) permite crear cuentas de Cliente o Propietario; el rol Administrador solo lo asigna otro administrador desde el módulo Usuarios (o con `createsuperuser`).
- Solo los administradores entran al panel. Los usuarios Inactivos o Bloqueados no pueden iniciar sesión.
- Un administrador no puede eliminar su propia cuenta.

## Sitio público
Búsqueda por texto/estilo, detalle público de tienda con reseñas y formulario para reportar problemas.

## Consideraciones
Las imágenes requieren Pillow. Bootstrap se carga desde CDN (se necesita internet). Cambia `SECRET_KEY`, `DEBUG` y `ALLOWED_HOSTS` antes de publicar.
