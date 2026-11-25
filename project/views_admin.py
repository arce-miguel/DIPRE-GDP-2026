from datetime import timedelta

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_date

from .models import Bitacora, Equipo, Incidencia, Prestamo, Rol, Usuario
from .views_encargado import administrador_required, encargado_required

POR_PAGINA = 50  # registros de la bitácora por página


def _bitacora_filtrada(request, tipo=None):
    """Registros de la bitácora según los filtros del formulario (GET): fecha, usuario y acción."""
    filtros = {
        'desde': request.GET.get('desde', ''),
        'hasta': request.GET.get('hasta', ''),
        'usuario': request.GET.get('usuario', '').strip(),
        'accion': request.GET.get('accion', '').strip(),
        'tipo': tipo or request.GET.get('tipo', ''),
    }
    registros = Bitacora.objects.select_related('usuario')
    if filtros['tipo'] in dict(Bitacora.TIPOS):
        registros = registros.filter(tipo=filtros['tipo'])
    else:
        filtros['tipo'] = ''
    desde, hasta = parse_date(filtros['desde']), parse_date(filtros['hasta'])
    if desde:
        registros = registros.filter(fecha_hora__date__gte=desde)
    if hasta:
        registros = registros.filter(fecha_hora__date__lte=hasta)
    if filtros['usuario']:
        registros = registros.filter(
            Q(usuario__nombre__icontains=filtros['usuario'])
            | Q(usuario__matricula__icontains=filtros['usuario'])
            | Q(usuario__num_empleado__icontains=filtros['usuario'])
            | Q(usuario__correo__icontains=filtros['usuario'])
            | Q(detalle__icontains=filtros['usuario']))
    if filtros['accion']:
        registros = registros.filter(accion__icontains=filtros['accion'])

    pagina = Paginator(registros, POR_PAGINA).get_page(request.GET.get('page'))
    consulta = request.GET.copy()
    consulta.pop('page', None)
    return pagina, filtros, consulta.urlencode()


def _pagina_bitacora(request, titulo, activo, tipo=None, con_tipo=False):
    pagina, filtros, consulta = _bitacora_filtrada(request, tipo)
    return render(request, 'gestion/encargado/encargado-bitacora.html', {
        'titulo': titulo, 'activo': activo, 'pagina': pagina, 'filtros': filtros,
        'consulta': consulta, 'con_tipo': con_tipo, 'tipos': Bitacora.TIPOS, 'equipos_modal': [],
    })


@encargado_required
def enc_historial(request):
    """El encargado ve las operaciones (préstamos, devoluciones, incidentes); los accesos son del admin."""
    return _pagina_bitacora(request, 'Historial', 'historial', tipo=Bitacora.OPERACION)


@administrador_required
def adm_bitacora(request):
    return _pagina_bitacora(request, 'Bitácora', 'bitacora', con_tipo=True)


@administrador_required
def adm_panel(request):
    ahora = timezone.now()
    hace_30 = ahora - timedelta(days=30)
    prestamos = Prestamo.objects
    estadisticas = {
        'usuarios': {
            'Solicitantes': Usuario.objects.filter(rol__nombre=Rol.SOLICITANTE, is_active=True).count(),
            'Encargados': Usuario.objects.filter(rol__nombre=Rol.ENCARGADO, is_active=True).count(),
            'Administradores': Usuario.objects.filter(rol__nombre=Rol.ADMINISTRADOR, is_active=True).count(),
        },
        'equipos': {etiqueta: Equipo.objects.filter(estado=clave).count() for clave, etiqueta in Equipo.ESTADOS},
        'prestamos': {
            'Pendientes': prestamos.filter(estado=Prestamo.PENDIENTE).count(),
            'Activos': prestamos.filter(estado=Prestamo.ACTIVO).count(),
            'Vencidos': sum(1 for p in prestamos.filter(estado=Prestamo.ACTIVO) if p.vencido),
            'Devueltos': prestamos.filter(estado=Prestamo.DEVUELTO).count(),
            'Solicitados en 30 días': prestamos.filter(fecha_solicitud__gte=hace_30).count(),
        },
        'incidencias': {
            'Abiertas': Incidencia.objects.abiertas().count(),
            'Adeudos sin saldar': Incidencia.objects.con_adeudo_pendiente().count(),
            'Cerradas': Incidencia.objects.cerradas().count(),
        },
    }
    return render(request, 'gestion/encargado/encargado-admin.html', {
        'estadisticas': estadisticas, 'equipos_modal': [],
        'accesos': Bitacora.objects.filter(tipo=Bitacora.ACCESO).select_related('usuario')[:8],
    })
