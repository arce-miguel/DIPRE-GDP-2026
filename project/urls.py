from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_todos, name='login'),
    path('panel/', views.panel_solicitante, name='panel_solicitante'),
    path('solicitar/', views.solicitar_equipo, name='solicitar_equipo'),
    path('prestamo/<int:pk>/', views.detalle_prestamo, name='detalle_prestamo'),
    path('adeudos/', views.mis_adeudos, name='mis_adeudos'),
]