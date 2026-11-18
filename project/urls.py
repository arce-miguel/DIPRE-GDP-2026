from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_todos, name='login'),
    path('encargado-dashb', views.enc_dash, name='enc-dash'), 


    path('encargado-pres',views.enc_pres, name='enc-pres'),   
    path('encargado-dev', views.enc_dev, name='enc-dev'),
    path('encargado-inci', views.enc_inci, name='enc-inci'),

]