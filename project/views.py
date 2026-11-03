from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .models import Prestamo

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
    # Pendiente: formulario de solicitud de equipo.
    if request.user.tiene_adeudos:
        return redirect('panel_solicitante')
    return render(request, 'gestion/solicitar_equipo.html')
