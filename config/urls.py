from django.contrib import admin
from django.urls import include, path
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

admin.site.site_header = _("Mebel Ombori — texnik boshqaruv")

urlpatterns = [
    # Django's built-in admin is kept for superusers / data fixes; day-to-day
    # administration happens in the app's own /admin-dashboard/ pages.
    path("django-admin/", admin.site.urls),
    path("api/", include("config.api_urls")),
    # POST /i18n/setlang/ with `language` switches the interface language.
    path("i18n/", include("django.conf.urls.i18n")),
    path("theme-preview/", TemplateView.as_view(template_name="theme_preview.html"), name="theme_preview"),
    path("", include("apps.users.urls")),
    path("", include("apps.inventory.urls")),
]
