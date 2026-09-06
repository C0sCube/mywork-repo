from django.urls import include, path
from webapp import views

urlpatterns = [
    path("", include("webapp.urls")),
]
