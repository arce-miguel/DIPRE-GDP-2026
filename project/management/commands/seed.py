from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from project.models import Categoria, DetallePrestamo, Equipo, Prestamo, Rol, Usuario

PASSWORD = 'demo1234'
SOLICITANTE_CORREO = 'solicitante@demo.local'
SOLICITANTE_PASSWORD = PASSWORD
# (correo, nombre, rol, matrícula, número de empleado)
USUARIOS = [
    (SOLICITANTE_CORREO, 'Solicitante Demo', Rol.SOLICITANTE, 'DEMO0001', None),
    ('ana@demo.local', 'Ana Pérez', Rol.SOLICITANTE, 'A01234', None),
    ('luis@demo.local', 'Luis Ramírez', Rol.SOLICITANTE, 'A01877', None),
    ('encargado@demo.local', 'Encargado Demo', Rol.ENCARGADO, None, 'ENC0001'),
    ('admin@demo.local', 'Administrador Demo', Rol.ADMINISTRADOR, None, 'ADM0001'),
]

EQUIPOS = [
    ('Laptop', Categoria.POR_DIAS, 'Dell', 'Latitude 3420', 3),
    ('Cámara', Categoria.POR_DIAS, 'Canon', 'EOS T7', 2),
    ('Proyector', Categoria.POR_HORAS, 'Epson', 'X49', 2),
    ('Bocina', Categoria.POR_HORAS, 'JBL', 'Partybox 110', 2),
]


class Command(BaseCommand):
    help = 'Crea datos de prueba (roles, categorías, equipos, usuarios y préstamos). Solo con DEBUG activo.'

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('seed solo se puede usar con DEBUG=True.')

        for nombre in (Rol.SOLICITANTE, Rol.ENCARGADO, Rol.ADMINISTRADOR):
            Rol.objects.get_or_create(nombre=nombre)

        for categoria, modalidad, marca, modelo, cantidad in EQUIPOS:
            cat, _ = Categoria.objects.get_or_create(nombre=categoria, defaults={'modalidad': modalidad})
            for n in range(1, cantidad + 1):
                Equipo.objects.get_or_create(
                    codigo_inventario=f'{categoria[:3].upper()}-{n:03d}',
                    defaults={'categoria': cat, 'marca': marca, 'modelo': modelo},
                )

        for correo, nombre, rol, matricula, num_empleado in USUARIOS:
            if not Usuario.objects.filter(correo=correo).exists():
                Usuario.objects.create_user(
                    correo, nombre, password=PASSWORD, rol=rol,
                    matricula=matricula, num_empleado=num_empleado)

        self._prestamos_de_ejemplo()

        self.stdout.write(self.style.SUCCESS('Datos de prueba listos.'))

    def _prestamos_de_ejemplo(self):
        """Un préstamo vencido y una solicitud pendiente, para ver el panel del encargado con datos."""
        if Prestamo.objects.exists():
            return
        ahora = timezone.now()
        encargado = Usuario.objects.get(correo='encargado@demo.local')
        ana = Usuario.objects.get(correo='ana@demo.local')
        luis = Usuario.objects.get(correo='luis@demo.local')

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
        DetallePrestamo.objects.create(prestamo=solicitud, equipo=Equipo.objects.get(codigo_inventario='CÁM-001'))
