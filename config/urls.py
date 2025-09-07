from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('shipments/', include('shipments.urls')),  # add this
    # path("shipmnets/", include("django.contrib.auth.urls")),  # 👈 this adds login/logout

]
