from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

handler403 = 'coffee.views.error_403'
handler404 = 'coffee.views.error_404'
handler500 = 'coffee.views.error_500'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('coffee.urls')),
    path('api/', include('coffee.api_urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)