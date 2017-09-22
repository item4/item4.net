from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^login/$', views.Login.as_view(), name='login'),
    url(r'^logout/$', views.LogoutView.as_view(), name='logout'),
    url(r'^register/$', views.Register.as_view(), name='register'),
    url(
        r'^confirm/$',
        views.Confirm.as_view(),
        name='account_email_verification_sent'  # override allauth default
    ),
    url(
        r'^confirm/(?P<key>[-:\w]+)/$',
        views.Confirm.as_view(),
        name="account_confirm_email"  # override allauth default
    ),
]
