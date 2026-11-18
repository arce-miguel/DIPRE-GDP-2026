from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class IdentificadorBackend(ModelBackend):
    """Permite iniciar sesión con matrícula, número de empleado o correo."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or password is None:
            return None
        Usuario = get_user_model()
        identificador = username.strip()
        try:
            usuario = Usuario.objects.get(
                Q(matricula__iexact=identificador)
                | Q(num_empleado__iexact=identificador)
                | Q(correo__iexact=identificador)
            )
        except (Usuario.DoesNotExist, Usuario.MultipleObjectsReturned):
            # Hash de relleno: el tiempo de respuesta no revela si el usuario existe
            Usuario().set_password(password)
            return None
        if usuario.check_password(password) and self.user_can_authenticate(usuario):
            return usuario
        return None
