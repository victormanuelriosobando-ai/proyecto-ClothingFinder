from decimal import Decimal
from functools import wraps

from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.core.paginator import Paginator
from django.db.models import Avg, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (ProductForm, PublicReviewForm, ReportAdminForm, ReportForm,
                    ReviewForm, SignUpForm, StoreForm, UsuarioForm)
from .models import Product, Report, Review, Store

# ---------------------------------------------------------------------------
# Configuración de los CRUD. Cada módulo se describe una sola vez aquí y las
# mismas vistas (lista, crear, detalle, editar y eliminar) sirven para todos.
# ---------------------------------------------------------------------------
CRUD = {
    'usuarios': {
        'model': User, 'form': UsuarioForm,
        'titulo': 'Usuarios', 'singular': 'usuario',
        'nuevo': 'Registrar usuario', 'icono': '♙',
        'columnas': [('Nombre', 'first_name'), ('Correo electrónico', 'email'),
                     ('Rol', 'perfil.rol'), ('Fecha de registro', 'date_joined'),
                     ('Estado', 'perfil.estado')],
        'detalle': [('Nombre completo', 'first_name'), ('Nombre de usuario', 'username'),
                    ('Correo electrónico', 'email'), ('Teléfono', 'perfil.telefono'),
                    ('Rol', 'perfil.rol'), ('Estado', 'perfil.estado'),
                    ('Fecha de registro', 'date_joined'), ('Último acceso', 'last_login')],
        'busqueda': ['first_name', 'username', 'email'],
        'relaciones': ['perfil'],
        'orden': '-date_joined',
        'aviso_eliminar': 'Sus reseñas se conservarán, pero dejarán de estar asociadas a esta cuenta.',
    },
    'tiendas': {
        'model': Store, 'form': StoreForm,
        'titulo': 'Tiendas', 'singular': 'tienda',
        'nuevo': 'Registrar tienda', 'icono': '▣',
        'columnas': [('Nombre', 'nombre'), ('Ciudad', 'ciudad'), ('Estilo', 'estilo'),
                     ('Correo', 'correo'), ('Estado', 'activa')],
        'busqueda': ['nombre', 'ciudad', 'estilo', 'correo'],
        'relaciones': [],
        'aviso_eliminar': 'También se eliminarán los productos y reseñas de esta tienda.',
    },
    'productos': {
        'model': Product, 'form': ProductForm,
        'titulo': 'Productos', 'singular': 'producto',
        'nuevo': 'Registrar producto', 'icono': '◇',
        'columnas': [('Producto', 'nombre'), ('Tienda', 'tienda'), ('Categoría', 'categoria'),
                     ('Estilo', 'estilo'), ('Precio', 'precio'), ('Unidades', 'unidades')],
        'busqueda': ['nombre', 'categoria', 'estilo', 'tienda__nombre'],
        'relaciones': ['tienda'],
        'aviso_eliminar': '',
    },
    'resenas': {
        'model': Review, 'form': ReviewForm,
        'titulo': 'Reseñas', 'singular': 'reseña',
        'nuevo': 'Registrar reseña', 'icono': '☆',
        'columnas': [('Tienda', 'tienda'), ('Autor', 'nombre_publico'),
                     ('Calificación', 'calificacion'), ('Comentario', 'comentario'),
                     ('Visible', 'visible')],
        'busqueda': ['nombre_publico', 'comentario', 'tienda__nombre'],
        'relaciones': ['tienda'],
        'aviso_eliminar': '',
    },
    'reportes': {
        'model': Report, 'form': ReportAdminForm,
        'titulo': 'Reportes', 'singular': 'reporte',
        'nuevo': 'Crear reporte', 'icono': '⚑',
        'columnas': [('Tipo', 'tipo'), ('Motivo', 'motivo'), ('Tienda', 'tienda'),
                     ('Estado', 'estado'), ('Fecha', 'creado')],
        'busqueda': ['motivo', 'detalle', 'correo_contacto', 'tienda__nombre'],
        'relaciones': ['tienda', 'producto'],
        'aviso_eliminar': '',
    },
}


def _valor(obj, nombre):
    """Devuelve el valor de un campo listo para mostrarse en una tabla."""
    if '.' in nombre:  # campo del perfil: 'perfil.rol'
        relacion, resto = nombre.split('.', 1)
        return _valor(getattr(obj, relacion), resto)
    campo = obj._meta.get_field(nombre)
    valor = getattr(obj, nombre)
    if campo.choices:
        return getattr(obj, f'get_{nombre}_display')()
    if isinstance(valor, bool):
        return 'Sí' if valor else 'No'
    if valor in (None, ''):
        return '—'
    if isinstance(valor, Decimal) and nombre == 'precio':
        return f'${valor:,.2f}'
    if hasattr(valor, 'strftime'):
        return valor.strftime('%d/%m/%Y %H:%M') if nombre == 'last_login' else valor.strftime('%d/%m/%Y')
    if isinstance(valor, str) and len(valor) > 70:
        return valor[:70] + '…'
    return valor


def admin_requerido(vista):
    """Solo los administradores (is_staff) pueden entrar al panel de gestión."""
    @wraps(vista)
    @login_required
    def envoltura(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, 'No tienes permisos para entrar al panel de administración.')
            return redirect('landing')
        return vista(request, *args, **kwargs)
    return envoltura


def _destino_tras_login(user):
    return 'panel' if user.is_staff else 'landing'


def _config(slug):
    return CRUD[slug]


def _contexto(slug, **extra):
    cfg = _config(slug)
    return {'slug': slug, 'cfg': cfg, 'titulo': cfg['titulo'], **extra}


# ---------------------------------------------------------------------------
# CRUD genérico (requiere sesión iniciada)
# ---------------------------------------------------------------------------
@admin_requerido
def lista(request, slug):
    cfg = _config(slug)
    registros = cfg['model'].objects.all()
    if cfg['relaciones']:
        registros = registros.select_related(*cfg['relaciones'])
    if cfg.get('orden'):
        registros = registros.order_by(cfg['orden'])

    q = request.GET.get('q', '').strip()
    if q:
        filtro = Q()
        for campo in cfg['busqueda']:
            filtro |= Q(**{f'{campo}__icontains': q})
        registros = registros.filter(filtro)

    pagina = Paginator(registros, 10).get_page(request.GET.get('page'))
    filas = [{'obj': o, 'celdas': [_valor(o, c) for _, c in cfg['columnas']]} for o in pagina]
    return render(request, 'finder/crud_lista.html',
                  _contexto(slug, pagina=pagina, filas=filas, q=q,
                            encabezados=[e for e, _ in cfg['columnas']]))


@admin_requerido
def crear(request, slug):
    cfg = _config(slug)
    form = cfg['form'](request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'{cfg["singular"].capitalize()} creado correctamente.')
        return redirect('lista', slug=slug)
    return render(request, 'finder/crud_form.html',
                  _contexto(slug, form=form, accion=cfg['nuevo'], editando=False))


@admin_requerido
def detalle(request, slug, pk):
    cfg = _config(slug)
    obj = get_object_or_404(cfg['model'], pk=pk)
    campos = []
    if cfg.get('detalle'):
        campos = [{'etiqueta': etiqueta, 'valor': _valor(obj, nombre), 'imagen': None}
                  for etiqueta, nombre in cfg['detalle']]
    for campo in ([] if campos else obj._meta.concrete_fields):
        if campo.name == 'id':
            continue
        imagen = getattr(obj, campo.name).url if campo.get_internal_type() == 'ImageField' \
            and getattr(obj, campo.name) else None
        campos.append({'etiqueta': str(campo.verbose_name).capitalize(),
                       'valor': '—' if imagen else _valor(obj, campo.name),
                       'imagen': imagen})
    return render(request, 'finder/crud_detalle.html',
                  _contexto(slug, obj=obj, campos=campos))


@admin_requerido
def editar(request, slug, pk):
    cfg = _config(slug)
    obj = get_object_or_404(cfg['model'], pk=pk)
    form = cfg['form'](request.POST or None, request.FILES or None, instance=obj)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'{cfg["singular"].capitalize()} actualizado correctamente.')
        return redirect('lista', slug=slug)
    return render(request, 'finder/crud_form.html',
                  _contexto(slug, form=form, obj=obj, accion=f'Editar {cfg["singular"]}',
                            editando=True))


@admin_requerido
def eliminar(request, slug, pk):
    cfg = _config(slug)
    obj = get_object_or_404(cfg['model'], pk=pk)
    if cfg['model'] is User and obj.pk == request.user.pk:
        messages.error(request, 'No puedes eliminar tu propia cuenta.')
        return redirect('lista', slug=slug)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, f'{cfg["singular"].capitalize()} eliminado correctamente.')
        return redirect('lista', slug=slug)
    return render(request, 'finder/crud_eliminar.html', _contexto(slug, obj=obj))


# ---------------------------------------------------------------------------
# Autenticación y panel
# ---------------------------------------------------------------------------
def signup(request):
    form = SignUpForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        auth_login(request, user)
        messages.success(request, 'Tu cuenta se creó correctamente.')
        return redirect(_destino_tras_login(user))
    return render(request, 'finder/auth.html',
                  {'form': form, 'titulo': 'Crear cuenta', 'modo': 'registro'})


def login_view(request):
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        auth_login(request, user)
        return redirect(_destino_tras_login(user))
    return render(request, 'finder/auth.html',
                  {'form': form, 'titulo': 'Iniciar sesión', 'modo': 'login'})


def logout_view(request):
    if request.method == 'POST':
        auth_logout(request)
    return redirect('landing')


@admin_requerido
def panel(request):
    return render(request, 'finder/panel.html', {
        'titulo': 'Panel principal',
        'tiendas': Store.objects.count(),
        'productos': Product.objects.count(),
        'resenas': Review.objects.count(),
        'reportes': Report.objects.filter(estado='pendiente').count(),
        'ultimas': Store.objects.order_by('-creada')[:5],
    })


# ---------------------------------------------------------------------------
# Sitio público
# ---------------------------------------------------------------------------
def landing(request):
    q = request.GET.get('q', '')
    estilo = request.GET.get('estilo', '')
    categoria = request.GET.get('categoria', '')
    tiendas = Store.objects.filter(activa=True)
    if q:
        tiendas = tiendas.filter(Q(nombre__icontains=q) | Q(ciudad__icontains=q)
                                 | Q(direccion__icontains=q) | Q(estilo__icontains=q))
    if estilo:
        tiendas = tiendas.filter(estilo__icontains=estilo)
    if categoria:
        tiendas = tiendas.filter(productos__categoria__icontains=categoria).distinct()
    return render(request, 'finder/landing.html',
                  {'tiendas': tiendas[:6], 'q': q, 'estilo': estilo, 'categoria': categoria})


def detalle_tienda(request, pk):
    tienda = get_object_or_404(Store, pk=pk, activa=True)
    form = PublicReviewForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        resena = form.save(commit=False)
        resena.tienda = tienda
        resena.usuario = request.user if request.user.is_authenticated else None
        resena.save()
        messages.success(request, 'Gracias por dejar tu reseña.')
        return redirect('detalle_tienda', pk=pk)
    resenas = tienda.resenas.filter(visible=True)
    return render(request, 'finder/detalle_tienda.html', {
        'tienda': tienda, 'form': form, 'resenas': resenas,
        'promedio': resenas.aggregate(p=Avg('calificacion'))['p'],
    })


def crear_reporte(request):
    form = ReportForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Tu reporte fue enviado para revisión.')
        return redirect('landing')
    return render(request, 'finder/formulario.html',
                  {'form': form, 'titulo': 'Reportar un problema'})
