from datetime import timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST

from . import services
from .models import Bitacora, DetallePrestamo, Equipo, Incidencia, Prestamo, limite_de_vencimiento
from .services import ErrorOperacion

POR_VENCER_HORAS = 24  # un préstamo activo se marca "por vencer" dentro de este margen


def encargado_required(vista):
    """Solo encargados (y administradores); a los demás los manda al acceso correspondiente."""
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), reverse('login') + '?tipo=encargado')
        if not request.user.es_encargado:
            messages.error(request, 'Tu cuenta no tiene acceso al módulo del encargado.')
            return redirect('index')
        return vista(request, *args, **kwargs)
    return envoltura


def _volver(request, defecto):
    """Redirección segura a la página desde la que se envió el formulario."""
    destino = request.POST.get('next', '')
    if destino and url_has_allowed_host_and_scheme(
            destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(destino)
    return redirect(defecto)


def _equipos_disponibles():
    return Equipo.objects.filter(estado=Equipo.DISPONIBLE).select_related('categoria')


def _clave_estado(prestamo, ahora):
    """Estado que se muestra: 'vencido' y 'por vencer' no se guardan, se calculan."""
    if prestamo.estado == Prestamo.ACTIVO:
        if prestamo.vencido:
            return 'vencido'
        if prestamo.fecha_limite - ahora <= timedelta(hours=POR_VENCER_HORAS):
            return 'por_vencer'
        return 'activo'
    return prestamo.estado


ETIQUETAS_ESTADO = {
    'pendiente': 'Pendiente',
    'activo': 'Activo',
    'por_vencer': 'Por vencer',
    'vencido': 'Vencido',
    'devuelto': 'Devuelto',
    'rechazado': 'Rechazado',
}


def _atraso(fecha_limite, hasta):
    """Texto del retraso entre la fecha límite y 'hasta' (vacío si no hay retraso)."""
    diferencia = hasta - fecha_limite
    if diferencia <= timedelta(0):
        return ''
    dias = diferencia.days
    if dias:
        return f'{dias} día{"s" if dias != 1 else ""}'
    horas = diferencia.seconds // 3600
    return f'{horas} hora{"s" if horas != 1 else ""}' if horas else 'menos de 1 hora'


# --- Principal --------------------------------------------------------------

@encargado_required
def enc_dash(request):
    ahora = timezone.now()
    vencidos = list(
        services.prestamos_vencidos()
        .select_related('solicitante').prefetch_related('detalles__equipo').order_by('fecha_limite')[:5])
    for prestamo in vencidos:
        prestamo.atraso = _atraso(prestamo.fecha_limite, ahora)

    return render(request, 'gestion/encargado/encargado-dashboard.html', {
        'conteos': {
            'prestamos': Prestamo.objects.filter(estado=Prestamo.ACTIVO).count(),
            'incidentes': Incidencia.objects.abiertas().count(),
            'pendientes': Prestamo.objects.filter(estado=Prestamo.PENDIENTE).count(),
        },
        'vencidos': vencidos,
        'equipos': _equipos_disponibles(),
        'actividad': Bitacora.objects.filter(tipo=Bitacora.OPERACION).select_related('usuario')[:6],
        'equipos_modal': _equipos_disponibles(),
    })


# --- Préstamos --------------------------------------------------------------

@encargado_required
def enc_pres(request):
    ahora = timezone.now()
    prestamos = list(
        Prestamo.objects.select_related('solicitante')
        .prefetch_related('detalles__equipo__categoria').order_by('-fecha_solicitud'))

    conteos = {clave: 0 for clave in ETIQUETAS_ESTADO}
    for prestamo in prestamos:
        prestamo.clave = _clave_estado(prestamo, ahora)
        prestamo.etiqueta = ETIQUETAS_ESTADO[prestamo.clave]
        prestamo.css = prestamo.clave.replace('_', '-')
        prestamo.busqueda = ' '.join(
            [prestamo.solicitante.nombre, prestamo.solicitante.identificador]
            + [f'{d.equipo.nombre} {d.equipo.codigo_inventario}' for d in prestamo.detalles.all()]
        ).lower()
        conteos[prestamo.clave] += 1

    return render(request, 'gestion/encargado/encargado-prestamos.html', {
        'prestamos': prestamos,
        'conteos': conteos,
        'total': len(prestamos),
        'motivos_rechazo': Prestamo.MOTIVOS_RECHAZO,
        'equipos_modal': _equipos_disponibles(),
    })


@encargado_required
@require_POST
def enc_prestamo_nuevo(request):
    solicitante = services.buscar_solicitante(request.POST.get('matricula'))
    limite = parse_datetime(request.POST.get('fecha_limite', ''))
    try:
        if limite is None:
            raise ErrorOperacion('Indica la fecha y hora límite de devolución.')
        if timezone.is_naive(limite):
            limite = timezone.make_aware(limite)
        prestamo = services.crear_prestamo_directo(
            request.user, solicitante, request.POST.get('equipo'), limite,
            request.POST.get('observaciones', ''))
    except ErrorOperacion as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f'Préstamo #{prestamo.pk} registrado para {prestamo.solicitante.nombre}.')
    return _volver(request, 'enc-pres')


@encargado_required
@require_GET
def enc_verificar(request):
    """Respuesta para el botón "Verificar" del modal de nuevo préstamo."""
    solicitante = services.buscar_solicitante(request.GET.get('matricula'))
    if solicitante is None:
        return JsonResponse({'encontrado': False, 'mensaje': 'Matrícula no encontrada.'})
    adeudos = solicitante.prestamos_vencidos().count()
    incidentes = solicitante.incidencias_pendientes().count()
    pendientes = []
    if adeudos:
        pendientes.append(f'{adeudos} préstamo{"s" if adeudos != 1 else ""} vencido{"s" if adeudos != 1 else ""}')
    if incidentes:
        pendientes.append(f'{incidentes} incidente{"s" if incidentes != 1 else ""} sin saldar')
    if pendientes:
        mensaje = f'{solicitante.nombre} tiene {" y ".join(pendientes)}. No puede recibir equipo.'
    else:
        mensaje = f'{solicitante.nombre}: sin adeudos ni incidentes. Puede recibir equipo.'
    return JsonResponse({
        'encontrado': True, 'nombre': solicitante.nombre,
        'puede': not pendientes, 'mensaje': mensaje,
    })


@encargado_required
@require_POST
def enc_prestamo_aprobar(request, pk):
    try:
        prestamo = services.aprobar_prestamo(request.user, pk)
    except ErrorOperacion as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f'Solicitud #{prestamo.pk} aprobada: equipo entregado a {prestamo.solicitante.nombre}.')
    return _volver(request, 'enc-pres')


@encargado_required
@require_POST
def enc_prestamo_rechazar(request, pk):
    try:
        prestamo = services.rechazar_prestamo(request.user, pk, request.POST.get('motivo', ''))
    except ErrorOperacion as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f'Solicitud #{prestamo.pk} rechazada.')
    return _volver(request, 'enc-pres')


# --- Devoluciones -----------------------------------------------------------

@encargado_required
def enc_dev(request):
    ahora = timezone.now()
    detalles = list(
        DetallePrestamo.objects
        .filter(prestamo__estado__in=[Prestamo.ACTIVO, Prestamo.DEVUELTO])
        .select_related('prestamo__solicitante', 'equipo__categoria')
        .order_by('-prestamo__fecha_solicitud', 'pk'))

    conteos = {'por_devolver': 0, 'vencido': 0, 'devuelto': 0}
    for detalle in detalles:
        prestamo = detalle.prestamo
        if detalle.devuelto:
            detalle.clave = 'devuelto'
            detalle.atraso = _atraso(prestamo.fecha_limite, detalle.fecha_devolucion)
        else:
            detalle.clave = _clave_estado(prestamo, ahora)
            detalle.atraso = _atraso(prestamo.fecha_limite, ahora)
        detalle.etiqueta = ETIQUETAS_ESTADO[detalle.clave]
        detalle.css = detalle.clave.replace('_', '-')
        detalle.vencido = detalle.clave == 'vencido'
        detalle.busqueda = (
            f'{prestamo.solicitante.nombre} {prestamo.solicitante.identificador} '
            f'{detalle.equipo.nombre} {detalle.equipo.codigo_inventario}').lower()
        if detalle.devuelto:
            conteos['devuelto'] += 1
        else:
            conteos['por_devolver'] += 1
            if detalle.vencido:
                conteos['vencido'] += 1

    return render(request, 'gestion/encargado/encargado-dev.html', {
        'detalles': detalles,
        'conteos': conteos,
        'equipos_modal': _equipos_disponibles(),
    })


@encargado_required
@require_POST
def enc_devolver(request):
    hubo_incidente = request.POST.get('incidente') == 'on'
    estado = request.POST.get('estado_devolucion') if hubo_incidente else DetallePrestamo.BUEN_ESTADO
    try:
        detalle = services.devolver_equipo(
            request.user, request.POST.get('detalle'), estado or DetallePrestamo.BUEN_ESTADO,
            request.POST.get('descripcion', ''))
    except ErrorOperacion as error:
        messages.error(request, str(error))
    else:
        mensaje = f'Devolución registrada: {detalle.equipo.nombre} · {detalle.equipo.codigo_inventario}.'
        if hubo_incidente:
            mensaje += ' Se abrió un incidente.'
        messages.success(request, mensaje)
    return _volver(request, 'enc-dev')


# --- Incidentes -------------------------------------------------------------

def _incidencia_a_dict(incidencia):
    equipo = incidencia.equipo
    prestamo = incidencia.prestamo
    abierta = (not incidencia.resuelta) or incidencia.adeudo_pendiente
    if prestamo:
        quien = prestamo.solicitante
        origen = f'Préstamo #{prestamo.pk}'
    else:
        quien = None
        origen = 'Revisión del equipo'

    resolucion = incidencia.get_resolucion_display() if incidencia.resuelta else ''
    if incidencia.forma_saldo:
        resolucion = (resolucion + ' · ' if resolucion else '') + incidencia.get_forma_saldo_display()

    return {
        'id': incidencia.pk,
        'equipo': equipo.nombre,
        'codigo': equipo.codigo_inventario,
        'estudiante': quien.nombre if quien else '—',
        'matricula': quien.identificador if quien else '',
        'tipo': incidencia.get_tipo_display(),
        'fecha': timezone.localtime(incidencia.fecha).date().isoformat(),
        'origen': origen,
        'descripcion': incidencia.descripcion,
        'abierta': abierta,
        'resuelta': incidencia.resuelta,
        'adeudo_pendiente': incidencia.adeudo_pendiente,
        'resuelto': (timezone.localtime(
            incidencia.fecha_saldo or incidencia.fecha_resolucion).date().isoformat()
            if not abierta and (incidencia.fecha_saldo or incidencia.fecha_resolucion) else None),
        'solucion': resolucion,
        'opciones': [{'clave': c, 'texto': t} for c, t in incidencia.opciones_resolucion],
    }


@encargado_required
def enc_inci(request):
    incidencias = (Incidencia.objects
                   .select_related('equipo', 'prestamo__solicitante').order_by('-fecha'))

    # Cada equipo con el último estudiante que lo tuvo (para el modal "Registrar incidente")
    equipos = []
    for equipo in Equipo.objects.exclude(estado=Equipo.BAJA):
        prestamo = services.ultimo_prestamo_de(equipo)
        quien = f' · {prestamo.solicitante.nombre} · {prestamo.solicitante.identificador}' if prestamo else ''
        equipos.append({'id': equipo.pk, 'texto': f'{equipo.nombre} · {equipo.codigo_inventario}{quien}'})

    return render(request, 'gestion/encargado/encargado-incidentes.html', {
        'incidentes': [_incidencia_a_dict(i) for i in incidencias],
        'equipos_incidente': equipos,
        'tipos_incidente': Incidencia.TIPOS,
        'formas_saldo': Incidencia.FORMAS_SALDO,
        'equipos_modal': [],
    })


@encargado_required
@require_POST
def enc_incidente_nuevo(request):
    try:
        incidencia = services.registrar_incidencia(
            request.user, request.POST.get('equipo'), request.POST.get('tipo', ''),
            request.POST.get('descripcion', ''))
    except ErrorOperacion as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f'Incidente registrado: {incidencia.equipo.nombre} · '
                                  f'{incidencia.equipo.codigo_inventario}.')
    return redirect('enc-inci')


@encargado_required
@require_POST
def enc_incidente_resolver(request, pk):
    try:
        services.resolver_incidencia(
            request.user, pk, request.POST.get('resolucion', ''), request.POST.get('forma_saldo', ''))
    except ErrorOperacion as error:
        messages.error(request, str(error))
    else:
        messages.success(request, 'Incidente actualizado.')
    return redirect('enc-inci')
