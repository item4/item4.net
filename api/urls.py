from django.conf.urls import include, url

from . import views

urlpatterns = [
    url(r'^auth/', include('api.auth.urls')),
    url(r'^users/', include('api.users.urls')),
    url(r'^$', views.index, name='index'),
]
