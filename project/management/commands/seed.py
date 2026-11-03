from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from project.models import Categoria, Equipo, Rol, Usuario

SOLICITANTE_CORREO = 'solicitante@demo.local'
SOLICITANTE_PASSWORD = 'demo1234'

EQUIPOS = [
    ('Laptop', Categoria.POR_DIAS, 'Dell', 'Latitude 3420', 3),
    ('Cámara', Categoria.POR_DIAS, 'Canon', 'EOS T7', 2),
    ('Proyector', Categoria.POR_HORAS, 'Epson', 'X49', 2),
    ('Bocina', Categoria.POR_HORAS, 'JBL', 'Partybox 110', 2),
]


class Command(BaseCommand):
    help = 'Crea datos de prueba (roles, categorías, equipos y un solicitante). Solo con DEBUG activo.'

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

        if not Usuario.objects.filter(correo=SOLICITANTE_CORREO).exists():
            Usuario.objects.create_user(
                SOLICITANTE_CORREO, 'Solicitante Demo', password=SOLICITANTE_PASSWORD, matricula='DEMO0001')

        self.stdout.write(self.style.SUCCESS('Datos de prueba listos.'))
