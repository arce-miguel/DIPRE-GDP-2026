from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField

from .models import (
    Bitacora, Categoria, DetallePrestamo, Equipo, Incidencia, Prestamo, Rol, Usuario,
)


class UsuarioCreationForm(forms.ModelForm):
    """Alta de usuarios desde el admin: la contraseña se guarda con hash, nunca en claro."""
    password1 = forms.CharField(label='Contraseña', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirmar contraseña', widget=forms.PasswordInput)

    class Meta:
        model = Usuario
        fields = ('nombre', 'correo', 'matricula', 'num_empleado', 'rol')

    def clean_password2(self):
        p1, p2 = self.cleaned_data.get('password1'), self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Las contraseñas no coinciden.')
        return p2

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.set_password(self.cleaned_data['password1'])
        if commit:
            usuario.save()
        return usuario


class UsuarioChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(
        label='Contraseña',
        help_text='Las contraseñas no se guardan en claro. Usa el enlace "Cambiar contraseña".')

    class Meta:
        model = Usuario
        fields = ('nombre', 'correo', 'matricula', 'num_empleado', 'rol', 'is_active', 'password')


@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    form = UsuarioChangeForm
    add_form = UsuarioCreationForm
    list_display = ('nombre', 'correo', 'matricula', 'num_empleado', 'rol', 'is_active')
    list_filter = ('rol', 'is_active')
    search_fields = ('nombre', 'correo', 'matricula', 'num_empleado')
    ordering = ('nombre',)
    filter_horizontal = ()
    fieldsets = (
        (None, {'fields': ('nombre', 'correo', 'password')}),
        ('Identificación', {'fields': ('matricula', 'num_empleado', 'rol')}),
        ('Estado', {'fields': ('is_active', 'last_login')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': (
            'nombre', 'correo', 'matricula', 'num_empleado', 'rol', 'password1', 'password2')}),
    )


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('nombre',)


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'modalidad')


@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = ('codigo_inventario', 'marca', 'modelo', 'categoria', 'estado')
    list_filter = ('categoria', 'estado')
    search_fields = ('codigo_inventario', 'marca', 'modelo', 'numero_serie')


class DetallePrestamoInline(admin.TabularInline):
    model = DetallePrestamo
    extra = 0
    raw_id_fields = ('equipo', 'usuario_devolucion')


@admin.register(Prestamo)
class PrestamoAdmin(admin.ModelAdmin):
    list_display = ('id', 'solicitante', 'estado', 'fecha_solicitud', 'fecha_limite')
    list_filter = ('estado',)
    search_fields = ('solicitante__nombre', 'solicitante__matricula')
    raw_id_fields = ('solicitante', 'usuario_registro')
    inlines = [DetallePrestamoInline]


@admin.register(Incidencia)
class IncidenciaAdmin(admin.ModelAdmin):
    list_display = ('equipo', 'tipo', 'fecha', 'resuelta', 'adeudo_saldado')
    list_filter = ('tipo', 'resuelta', 'adeudo_saldado')
    raw_id_fields = ('equipo', 'prestamo', 'usuario_registro', 'usuario_resolucion', 'usuario_saldo')


@admin.register(Bitacora)
class BitacoraAdmin(admin.ModelAdmin):
    list_display = ('fecha_hora', 'tipo', 'usuario', 'accion', 'detalle')
    list_filter = ('tipo',)
    search_fields = ('accion', 'detalle', 'usuario__nombre')
    readonly_fields = ('tipo', 'usuario', 'accion', 'entidad', 'id_registro', 'detalle', 'fecha_hora')

    def has_add_permission(self, request):
        return False  # la bitácora solo la escribe el sistema
