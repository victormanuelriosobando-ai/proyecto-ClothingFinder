from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Product, Report, Review, Store


class PublicPagesTests(TestCase):
    def test_landing_loads(self):
        self.assertEqual(self.client.get(reverse('landing')).status_code, 200)

    def test_crud_requires_login(self):
        resp = self.client.get(reverse('lista', args=['tiendas']))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp.url)

    def test_public_review_and_report(self):
        tienda = Store.objects.create(nombre='T', correo='t@t.com', direccion='x')
        resp = self.client.post(reverse('detalle_tienda', args=[tienda.pk]),
                                {'nombre_publico': 'Ana', 'calificacion': 5, 'comentario': 'Genial'})
        self.assertRedirects(resp, reverse('detalle_tienda', args=[tienda.pk]))
        self.assertEqual(tienda.resenas.count(), 1)
        resp = self.client.post(reverse('crear_reporte'),
                                {'tipo': 'otro', 'motivo': 'm', 'detalle': 'd'})
        self.assertRedirects(resp, reverse('landing'))
        self.assertEqual(Report.objects.count(), 1)


class CrudTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('admin', password='x', is_staff=True)
        self.client.force_login(self.admin)
        self.tienda = Store.objects.create(nombre='Urban', correo='u@u.com', direccion='Cra 1')

    def test_all_lists_and_forms_load(self):
        for slug in ('usuarios', 'tiendas', 'productos', 'resenas', 'reportes'):
            for nombre in ('lista', 'crear'):
                self.assertEqual(self.client.get(reverse(nombre, args=[slug])).status_code, 200, (slug, nombre))
        self.assertEqual(self.client.get(reverse('panel')).status_code, 200)

    def test_store_full_cycle(self):
        datos = {'nombre': 'Nueva', 'correo': 'n@n.com', 'direccion': 'Calle 2',
                 'ciudad': 'Itagüí', 'activa': 'on'}
        self.client.post(reverse('crear', args=['tiendas']), datos)
        tienda = Store.objects.get(nombre='Nueva')
        self.assertEqual(self.client.get(reverse('detalle', args=['tiendas', tienda.pk])).status_code, 200)

        datos['nombre'] = 'Editada'
        self.client.post(reverse('editar', args=['tiendas', tienda.pk]), datos)
        tienda.refresh_from_db()
        self.assertEqual(tienda.nombre, 'Editada')

        self.assertEqual(self.client.get(reverse('eliminar', args=['tiendas', tienda.pk])).status_code, 200)
        self.assertTrue(Store.objects.filter(pk=tienda.pk).exists())  # GET no borra
        self.client.post(reverse('eliminar', args=['tiendas', tienda.pk]))
        self.assertFalse(Store.objects.filter(pk=tienda.pk).exists())

    def test_product_review_report_cycle(self):
        casos = {
            'productos': (Product, {'tienda': self.tienda.pk, 'nombre': 'Chaqueta', 'categoria': 'chaquetas',
                                    'precio': '100000', 'unidades': 3}, 'nombre', 'Chaqueta 2'),
            'resenas': (Review, {'tienda': self.tienda.pk, 'nombre_publico': 'Ana', 'calificacion': 4,
                                 'comentario': 'Bien', 'visible': 'on'}, 'comentario', 'Mejor'),
            'reportes': (Report, {'tipo': 'otro', 'motivo': 'Falla', 'detalle': 'x', 'estado': 'pendiente'},
                         'estado', 'resuelto'),
        }
        for slug, (modelo, datos, campo, nuevo) in casos.items():
            self.client.post(reverse('crear', args=[slug]), datos)
            obj = modelo.objects.get()
            self.assertEqual(self.client.get(reverse('detalle', args=[slug, obj.pk])).status_code, 200)
            self.client.post(reverse('editar', args=[slug, obj.pk]), {**datos, campo: nuevo})
            obj.refresh_from_db()
            self.assertEqual(str(getattr(obj, campo)), nuevo, slug)
            self.client.post(reverse('eliminar', args=[slug, obj.pk]))
            self.assertEqual(modelo.objects.count(), 0, slug)

    def test_search(self):
        Store.objects.create(nombre='Otra', correo='o@o.com', direccion='z')
        resp = self.client.get(reverse('lista', args=['tiendas']), {'q': 'Urban'})
        self.assertContains(resp, 'Urban')
        self.assertNotContains(resp, 'Otra')

    def test_sidebar_has_dropdowns(self):
        resp = self.client.get(reverse('panel'))
        for texto in ('Listado de usuarios', 'Registrar usuario', 'Listar tiendas', 'Registrar tienda', 'Listar productos', 'Listar reseñas', 'Listar reportes'):
            self.assertContains(resp, texto)
        self.assertContains(resp, 'data-bs-toggle="collapse"')


class UsuariosTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('admin', password='x', is_staff=True)
        self.client.force_login(self.admin)

    def datos(self, **extra):
        base = {'first_name': 'Laura Gómez', 'username': 'laura', 'email': 'laura@correo.com',
                'telefono': '300', 'rol': 'propietario', 'estado': 'activo', 'password': 'clave12345'}
        return {**base, **extra}

    def test_admin_profile_is_created_with_staff_role(self):
        self.assertEqual(self.admin.perfil.rol, 'administrador')

    def test_user_full_cycle(self):
        self.client.post(reverse('crear', args=['usuarios']), self.datos())
        user = User.objects.get(username='laura')
        self.assertTrue(user.check_password('clave12345'))
        self.assertEqual(user.perfil.rol, 'propietario')
        self.assertFalse(user.is_staff)
        self.assertEqual(self.client.get(reverse('detalle', args=['usuarios', user.pk])).status_code, 200)

        # Editar sin contraseña conserva la anterior; cambiar a administrador da acceso al panel
        self.client.post(reverse('editar', args=['usuarios', user.pk]),
                         self.datos(first_name='Laura G.', rol='administrador', password=''))
        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Laura G.')
        self.assertTrue(user.check_password('clave12345'))
        self.assertTrue(user.is_staff)

        self.client.post(reverse('eliminar', args=['usuarios', user.pk]))
        self.assertFalse(User.objects.filter(pk=user.pk).exists())

    def test_blocked_user_cannot_login(self):
        self.client.post(reverse('crear', args=['usuarios']), self.datos(estado='bloqueado'))
        self.client.logout()
        self.assertFalse(self.client.login(username='laura', password='clave12345'))

    def test_cannot_delete_yourself(self):
        self.client.post(reverse('eliminar', args=['usuarios', self.admin.pk]))
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())

    def test_duplicate_email_rejected(self):
        self.client.post(reverse('crear', args=['usuarios']), self.datos())
        self.client.post(reverse('crear', args=['usuarios']), self.datos(username='otra'))
        self.assertEqual(User.objects.filter(email='laura@correo.com').count(), 1)

    def test_customer_cannot_access_panel(self):
        cliente = User.objects.create_user('cli', password='x')
        self.client.force_login(cliente)
        for nombre, args in (('panel', []), ('lista', ['tiendas']), ('lista', ['usuarios'])):
            resp = self.client.get(reverse(nombre, args=args))
            self.assertRedirects(resp, reverse('landing'), fetch_redirect_response=False)

    def test_public_signup_creates_role_and_redirects(self):
        self.client.logout()
        resp = self.client.post(reverse('registro'), {
            'first_name': 'Pedro Díaz', 'email': 'pedro@correo.com', 'telefono': '311',
            'rol': 'propietario', 'username': 'pedro', 'password1': 'Clave-segura-9',
            'password2': 'Clave-segura-9', 'acepto': 'on'})
        self.assertRedirects(resp, reverse('landing'), fetch_redirect_response=False)
        user = User.objects.get(username='pedro')
        self.assertEqual((user.perfil.rol, user.perfil.telefono, user.is_staff), ('propietario', '311', False))

    def test_signup_cannot_choose_admin_role(self):
        self.client.logout()
        self.client.post(reverse('registro'), {
            'first_name': 'X', 'email': 'x@x.com', 'rol': 'administrador', 'username': 'x',
            'password1': 'Clave-segura-9', 'password2': 'Clave-segura-9', 'acepto': 'on'})
        self.assertFalse(User.objects.filter(username='x').exists())
