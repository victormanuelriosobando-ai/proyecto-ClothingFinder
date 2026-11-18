from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Product, Profile, Report, Review, Store


class BootstrapMixin:
    """Aplica las clases de Bootstrap a todos los campos del formulario."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                css = 'form-check-input'
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                css = 'form-select'
            else:
                css = 'form-control'
            widget.attrs['class'] = f"{widget.attrs.get('class', '')} {css}".strip()


class StoreForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Store
        fields = ['nombre', 'responsable', 'correo', 'telefono', 'direccion', 'ciudad',
                  'estilo', 'descripcion', 'horario', 'latitud', 'longitud', 'activa']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 3})}


class ProductForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Product
        fields = ['tienda', 'nombre', 'referencia', 'categoria', 'estilo', 'talla',
                  'color', 'precio', 'unidades', 'imagen', 'descripcion']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 3})}


class ReviewForm(BootstrapMixin, forms.ModelForm):
    """Formulario de administración de reseñas."""

    class Meta:
        model = Review
        fields = ['tienda', 'nombre_publico', 'calificacion', 'comentario', 'visible']
        widgets = {'comentario': forms.Textarea(attrs={'rows': 3})}


class PublicReviewForm(BootstrapMixin, forms.ModelForm):
    """Formulario público: la tienda se toma de la URL, no del formulario."""

    class Meta:
        model = Review
        fields = ['nombre_publico', 'calificacion', 'comentario']
        widgets = {'comentario': forms.Textarea(attrs={'rows': 3})}


class ReportForm(BootstrapMixin, forms.ModelForm):
    """Formulario público para reportar un problema."""

    class Meta:
        model = Report
        fields = ['tipo', 'tienda', 'producto', 'correo_contacto', 'motivo', 'detalle']
        widgets = {'detalle': forms.Textarea(attrs={'rows': 4})}


class ReportAdminForm(ReportForm):
    """Formulario de administración: además permite gestionar el estado."""

    class Meta(ReportForm.Meta):
        fields = ReportForm.Meta.fields + ['estado']


class SignUpForm(BootstrapMixin, UserCreationForm):
    """Registro público: el usuario elige si es cliente o propietario de tienda."""
    first_name = forms.CharField(max_length=150, label='Nombre completo')
    email = forms.EmailField(label='Correo electrónico')
    telefono = forms.CharField(max_length=25, required=False, label='Teléfono')
    rol = forms.ChoiceField(label='Tipo de cuenta',
                            choices=[('cliente', 'Cliente'), ('propietario', 'Propietario de tienda')])
    acepto = forms.BooleanField(label='Acepto el tratamiento de datos y las condiciones de uso.')

    class Meta:
        model = User
        fields = ('first_name', 'email', 'telefono', 'rol', 'username', 'password1', 'password2', 'acepto')

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Ya existe una cuenta con este correo.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.save()
        perfil = Profile.objects.get_or_create(user=user)[0]
        perfil.rol = self.cleaned_data['rol']
        perfil.telefono = self.cleaned_data['telefono']
        perfil.save()
        return user


class UsuarioForm(BootstrapMixin, forms.ModelForm):
    """Formulario de administración de usuarios (cuenta + perfil)."""
    telefono = forms.CharField(max_length=25, required=False, label='Teléfono')
    rol = forms.ChoiceField(choices=Profile.ROLES, label='Rol')
    estado = forms.ChoiceField(choices=Profile.ESTADOS, label='Estado', initial='activo')
    password = forms.CharField(widget=forms.PasswordInput(render_value=False), required=False,
                               label='Contraseña')

    class Meta:
        model = User
        fields = ['first_name', 'username', 'email']
        labels = {'first_name': 'Nombre completo', 'username': 'Nombre de usuario',
                  'email': 'Correo electrónico'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['email'].required = True
        self.order_fields(['first_name', 'username', 'email', 'telefono', 'rol', 'estado', 'password'])
        if self.instance.pk:
            perfil = Profile.objects.get_or_create(user=self.instance)[0]
            self.initial.update(telefono=perfil.telefono, rol=perfil.rol, estado=perfil.estado)
            self.fields['password'].help_text = 'Déjala vacía para conservar la contraseña actual.'
        else:
            self.fields['password'].required = True
            self.fields['password'].help_text = 'Mínimo 8 caracteres.'

    def clean_email(self):
        email = self.cleaned_data['email']
        repetidos = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if repetidos.exists():
            raise forms.ValidationError('Ya existe un usuario con este correo.')
        return email

    def clean_password(self):
        clave = self.cleaned_data['password']
        if clave and len(clave) < 8:
            raise forms.ValidationError('La contraseña debe tener al menos 8 caracteres.')
        return clave

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data['password']:
            user.set_password(self.cleaned_data['password'])
        user.save()
        perfil = Profile.objects.get_or_create(user=user)[0]
        perfil.telefono = self.cleaned_data['telefono']
        perfil.rol = self.cleaned_data['rol']
        perfil.estado = self.cleaned_data['estado']
        perfil.save()
        return user
