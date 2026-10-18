from django.shortcuts import render

# Create your views here.
def index(request):
    return render(request, 'gestion/index.html')

def login_todos(request):
    tipo = request.GET.get('tipo', 'estudiante')
    
    if tipo == 'encargado':
        titulo_login = "ENCARGADO"
        subtitulo = "Ingrese datos de encargado"
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
def enc_dash(request):
    return render(request, 'gestion/encargado/encargado-dashboard.html')
