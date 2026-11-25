from django.urls import path
from . import views, views_admin as adm, views_encargado as enc

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_todos, name='login'),
    path('logout/', views.cerrar_sesion, name='logout'),

    # Solicitante
    path('panel/', views.panel_solicitante, name='panel_solicitante'),
    path('solicitar/', views.solicitar_equipo, name='solicitar_equipo'),
    path('prestamo/<int:pk>/', views.detalle_prestamo, name='detalle_prestamo'),
    path('mis-prestamos/', views.mis_prestamos, name='mis_prestamos'),
    path('adeudos/', views.mis_adeudos, name='mis_adeudos'),
    path('catalogo/', views.catalogo, name='catalogo'),
    path('reglas/', views.reglas, name='reglas'),
    path('cuenta/', views.mi_cuenta, name='mi_cuenta'),

    # Encargado: páginas
    path('encargado/dashboard', enc.enc_dash, name='enc-dash'),
    path('encargado/prestamo', enc.enc_pres, name='enc-pres'),
    path('encargado/devoluciones', enc.enc_dev, name='enc-dev'),
    path('encargado/incidentes', enc.enc_inci, name='enc-inci'),
    path('encargado/vencidos', enc.enc_vencidos, name='enc-ven'),
    path('encargado/inventario', enc.enc_inventario, name='enc-inven'),
    path('encargado/adeudos', enc.enc_adeudos, name='enc-adeu'),
    path('encargado/historial', adm.enc_historial, name='enc-historial'),

    # Administrador
    path('administrador/panel', adm.adm_panel, name='adm-panel'),
    path('administrador/bitacora', adm.adm_bitacora, name='adm-bitacora'),

    # Encargado: acciones sobre la base de datos
    path('encargado/verificar/', enc.enc_verificar, name='enc-verificar'),
    path('encargado/prestamo/nuevo/', enc.enc_prestamo_nuevo, name='enc-prestamo-nuevo'),
    path('encargado/prestamo/<int:pk>/aprobar/', enc.enc_prestamo_aprobar, name='enc-prestamo-aprobar'),
    path('encargado/prestamo/<int:pk>/rechazar/', enc.enc_prestamo_rechazar, name='enc-prestamo-rechazar'),
    path('encargado/devolver/', enc.enc_devolver, name='enc-devolver'),
    path('encargado/incidente/nuevo/', enc.enc_incidente_nuevo, name='enc-incidente-nuevo'),
    path('encargado/incidente/<int:pk>/resolver/', enc.enc_incidente_resolver, name='enc-incidente-resolver'),
]
