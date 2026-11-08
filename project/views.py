from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import SolicitudPrestamoForm
from .models import Equipo, Prestamo

# Create your views here.
def index(request):
    return render(request, 'gestion/index.html')

def login_todos(request):
    tipo = request.GET.get('tipo', 'estudiante')
    
    if tipo == 'encargado':
        titulo_login = "ENCARGADO"
        subtitulo = "Ingrese con su cuenta y clave institucional docente"
    elif tipo == 'ADMIN':
        titulo_login = "ADMINISTRADOR"
        subtitulo = "Ingrese datos de administrador"
    else:
        titulo_login = "ESTUDIANTE"
        subtitulo = "Ingrese con sus credenciales de estudiante"

    return render(request, 'gestion/login.html', {
        'titulo_login': titulo_login,
        'subtitulo': subtitulo,
        'tipo': tipo
    })


@login_required
def panel_solicitante(request):
    usuario = request.user
    if not usuario.es_solicitante:
        return redirect('index')

    prestamos = list(
        usuario.prestamos_solicitados
        .prefetch_related('detalles__equipo__categoria')
        .order_by('-fecha_solicitud')
    )
    resumen = {
        'activos': sum(1 for p in prestamos if p.estado == Prestamo.ACTIVO),
        'vencidos': sum(1 for p in prestamos if p.vencido),
        'pendientes': sum(1 for p in prestamos if p.estado == Prestamo.PENDIENTE),
    }
    incidencias = list(usuario.incidencias_pendientes().select_related('equipo__categoria'))
    return render(request, 'gestion/panel_solicitante.html', {
        'prestamos': prestamos,
        'resumen': resumen,
        'tiene_adeudos': bool(incidencias) or resumen['vencidos'] > 0,
        'incidencias_pendientes': incidencias,
    })


@login_required
def solicitar_equipo(request):
    usuario = request.user
    if not usuario.es_solicitante:
        return redirect('index')
    if usuario.tiene_adeudos:
        messages.error(request, 'Tienes adeudos pendientes y no puedes solicitar equipos.')
        return redirect('panel_solicitante')

    form = SolicitudPrestamoForm(request.POST or None, solicitante=usuario)
    if request.method == 'POST' and form.is_valid():
        form.guardar()
        messages.success(request, 'Tu solicitud fue enviada. Espera la aprobación del encargado.')
        return redirect('panel_solicitante')

    disponibles = Equipo.objects.filter(estado=Equipo.DISPONIBLE).select_related('categoria')
    grupos = {}
    for equipo in disponibles:
        grupos.setdefault(equipo.categoria, []).append(equipo)
    seleccionados = {int(pk) for pk in request.POST.getlist('equipos') if pk.isdigit()}
    return render(request, 'gestion/solicitar_equipo.html', {
        'form': form,
        'grupos': grupos.items(),
        'seleccionados': seleccionados,
        'max_equipos': settings.SOLICITUD_MAX_EQUIPOS,
    })


@login_required
def detalle_prestamo(request, pk):
    usuario = request.user
    if not usuario.es_solicitante:
        return redirect('index')
    prestamo = get_object_or_404(
        usuario.prestamos_solicitados.prefetch_related('detalles__equipo__categoria'), pk=pk)
    return render(request, 'gestion/detalle_prestamo.html', {'prestamo': prestamo})


@login_required
def mis_adeudos(request):
    usuario = request.user
    if not usuario.es_solicitante:
        return redirect('index')
    return render(request, 'gestion/mis_adeudos.html', {
        'vencidos': usuario.prestamos_vencidos().prefetch_related('detalles__equipo'),
        'incidencias': usuario.incidencias_pendientes().select_related('equipo', 'prestamo'),
    })
