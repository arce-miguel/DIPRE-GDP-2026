from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from project.models import Categoria, DetallePrestamo, Equipo, Prestamo, Rol, Usuario

PASSWORD = 'dipre123'
# (correo, nombre, rol, matrícula, número de empleado)
# Para entrar basta con la matrícula o el número de empleado: s01, e01, admin...
USUARIOS = [
    ('s01@demo.local', 'Solicitante 01', Rol.SOLICITANTE, 's01', None),
    ('s02@demo.local', 'Solicitante 02', Rol.SOLICITANTE, 's02', None),
    ('s03@demo.local', 'Solicitante 03', Rol.SOLICITANTE, 's03', None),
    ('e01@demo.local', 'Encargado 01', Rol.ENCARGADO, None, 'e01'),
    ('e02@demo.local', 'Encargado 02', Rol.ENCARGADO, None, 'e02'),
    ('admin@demo.local', 'Administrador', Rol.ADMINISTRADOR, None, 'admin'),
]
# Alumnos 23210001 a 23210009 y encargados 2101 a 2103, para hacer pruebas
USUARIOS += [
    (f'2321000{n}@demo.local', f'Alumno 2321000{n}', Rol.SOLICITANTE, f'2321000{n}', None)
    for n in range(1, 10)
]
USUARIOS += [
    (f'210{n}@demo.local', f'Encargado 210{n}', Rol.ENCARGADO, None, f'210{n}')
    for n in range(1, 4)
]

# (categoría, modalidad, prefijo del código, marca, modelo, cantidad)
# El nombre que ve el usuario es "marca modelo"; en lo genérico la marca es el tipo (p. ej. "Cable HDMI").
EQUIPOS = [
    ('Laptop', Categoria.POR_DIAS, 'LAP', 'Dell', 'Latitude 3420', 3),
    ('Proyector', Categoria.POR_HORAS, 'PRO', 'Epson', 'X49', 2),
    ('Bocina', Categoria.POR_HORAS, 'BOC', 'JBL', 'Partybox 110', 2),
    ('Cables', Categoria.POR_HORAS, 'HDMI', 'Cable', 'HDMI', 3),
    ('Cables', Categoria.POR_HORAS, 'UTP', 'Cable', 'UTP', 3),
    ('Cables', Categoria.POR_HORAS, 'AUX', 'Cable', 'Auxiliar 3.5 mm', 3),
    ('Cables', Categoria.POR_HORAS, 'USBC', 'Cable', 'USB-C', 3),
    ('Cables', Categoria.POR_HORAS, 'PON', 'Ponchadora', 'RJ45', 2),
    ('Mouse', Categoria.POR_HORAS, 'MOU', 'Mouse', 'Genérico', 4),
    ('Micrófono', Categoria.POR_HORAS, 'MIC', 'Micrófono', 'Genérico', 3),
    ('Teclado', Categoria.POR_HORAS, 'TEC', 'Teclado', 'Genérico', 3),
]


class Command(BaseCommand):
    help = 'Crea datos de prueba (roles, categorías, equipos, usuarios y préstamos). Solo con DEBUG activo.'

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('seed solo se puede usar con DEBUG=True.')

        for nombre in (Rol.SOLICITANTE, Rol.ENCARGADO, Rol.ADMINISTRADOR):
            Rol.objects.get_or_create(nombre=nombre)

        for categoria, modalidad, prefijo, marca, modelo, cantidad in EQUIPOS:
            cat, _ = Categoria.objects.get_or_create(nombre=categoria, defaults={'modalidad': modalidad})
            for n in range(1, cantidad + 1):
                Equipo.objects.get_or_create(
                    codigo_inventario=f'{prefijo}-{n:03d}',
                    defaults={'categoria': cat, 'marca': marca, 'modelo': modelo},
                )

        for correo, nombre, rol, matricula, num_empleado in USUARIOS:
            usuario = Usuario.objects.filter(correo=correo).first()
            if usuario is None:
                Usuario.objects.create_user(
                    correo, nombre, password=PASSWORD, rol=rol,
                    matricula=matricula, num_empleado=num_empleado)
            else:
                # Ya existe (de un seed anterior): se deja igual que la lista de arriba.
                usuario.nombre = nombre
                usuario.rol, _ = Rol.objects.get_or_create(nombre=rol)
                usuario.matricula = matricula
                usuario.num_empleado = num_empleado
                usuario.set_password(PASSWORD)
                usuario.save()

        self._prestamos_de_ejemplo()

        self.stdout.write(self.style.SUCCESS('Datos de prueba listos.'))

    def _prestamos_de_ejemplo(self):
        """Un préstamo vencido y una solicitud pendiente, para ver el panel del encargado con datos."""
        if Prestamo.objects.exists():
            return
        ahora = timezone.now()
        encargado = Usuario.objects.get(correo='e01@demo.local')
        ana = Usuario.objects.get(correo='s01@demo.local')
        luis = Usuario.objects.get(correo='s02@demo.local')

        laptop = Equipo.objects.get(codigo_inventario='LAP-001')
        prestamo = Prestamo.objects.create(
            solicitante=ana, usuario_registro=encargado, estado=Prestamo.ACTIVO,
            fecha_entrega=ahora - timedelta(days=6), fecha_limite=ahora - timedelta(days=2),
            motivo_tipo='tarea', motivo='Proyecto final')
        DetallePrestamo.objects.create(prestamo=prestamo, equipo=laptop)
        laptop.estado = Equipo.PRESTADO
        laptop.save(update_fields=['estado'])

        solicitud = Prestamo.objects.create(
            solicitante=luis, fecha_limite=ahora + timedelta(days=2), motivo_tipo='practica')
        DetallePrestamo.objects.create(prestamo=solicitud, equipo=Equipo.objects.get(codigo_inventario='LAP-002'))
