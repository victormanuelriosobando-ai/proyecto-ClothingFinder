from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

class Store(models.Model):
    nombre = models.CharField(max_length=120)
    responsable = models.CharField(max_length=120, blank=True)
    correo = models.EmailField()
    telefono = models.CharField(max_length=25, blank=True)
    direccion = models.CharField(max_length=220)
    ciudad = models.CharField(max_length=80, default='Medellín')
    estilo = models.CharField(max_length=80, blank=True, help_text='Ej. urbano, elegante, vintage')
    descripcion = models.TextField(blank=True)
    horario = models.CharField(max_length=180, blank=True)
    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    activa = models.BooleanField(default=True)
    creada = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['nombre']
    def __str__(self): return self.nombre

class Product(models.Model):
    tienda = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='productos')
    nombre = models.CharField(max_length=140)
    referencia = models.CharField(max_length=80, blank=True)
    categoria = models.CharField(max_length=80, help_text='Ej. chaquetas, pantalones, zapatos')
    estilo = models.CharField(max_length=80, blank=True)
    talla = models.CharField(max_length=60, blank=True)
    color = models.CharField(max_length=60, blank=True)
    precio = models.DecimalField(max_digits=12, decimal_places=2)
    unidades = models.PositiveIntegerField(default=0)
    imagen = models.ImageField(upload_to='catalogo/', blank=True, null=True)
    descripcion = models.TextField(blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['nombre']
    def __str__(self): return self.nombre

class Review(models.Model):
    tienda = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='resenas')
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    nombre_publico = models.CharField(max_length=100)
    calificacion = models.PositiveSmallIntegerField(choices=[(1,'1 - Muy mala'),(2,'2 - Mala'),(3,'3 - Regular'),(4,'4 - Buena'),(5,'5 - Excelente')])
    comentario = models.TextField()
    visible = models.BooleanField(default=True)
    creada = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-creada']
    def __str__(self): return f'{self.tienda} - {self.calificacion}/5'

class Report(models.Model):
    TIPOS = [('tienda','Tienda'),('producto','Producto'),('resena','Reseña'),('usuario','Usuario'),('otro','Otro')]
    ESTADOS = [('pendiente','Pendiente'),('revision','En revisión'),('resuelto','Resuelto'),('descartado','Descartado')]
    tipo = models.CharField(max_length=20, choices=TIPOS)
    tienda = models.ForeignKey(Store, on_delete=models.SET_NULL, null=True, blank=True)
    producto = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    correo_contacto = models.EmailField(blank=True)
    motivo = models.CharField(max_length=140)
    detalle = models.TextField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    creado = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-creado']
    def __str__(self): return f'Reporte #{self.pk}: {self.motivo}'


class Profile(models.Model):
    """Datos adicionales del usuario: rol, teléfono y estado de la cuenta."""
    ROLES = [('cliente', 'Cliente'), ('propietario', 'Propietario de tienda'),
             ('administrador', 'Administrador')]
    ESTADOS = [('activo', 'Activo'), ('inactivo', 'Inactivo'), ('bloqueado', 'Bloqueado')]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    telefono = models.CharField(max_length=25, blank=True)
    rol = models.CharField(max_length=20, choices=ROLES, default='cliente')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='activo')

    def __str__(self):
        return f'{self.user} ({self.get_rol_display()})'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # El estado y el rol controlan el acceso real: solo los usuarios activos pueden iniciar
        # sesión y solo los administradores entran al panel de gestión.
        activo = self.estado == 'activo'
        es_staff = self.rol == 'administrador' or self.user.is_superuser
        if self.user.is_active != activo or self.user.is_staff != es_staff:
            User.objects.filter(pk=self.user_id).update(is_active=activo, is_staff=es_staff)


@receiver(post_save, sender=User)
def crear_perfil(sender, instance, created, **kwargs):
    if created:
        rol = 'administrador' if (instance.is_superuser or instance.is_staff) else 'cliente'
        Profile.objects.create(user=instance, rol=rol)
