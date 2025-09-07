from django.urls import path
from . import views
from django.contrib.auth import views as auth_views


urlpatterns = [

    path("login/", views.login_view, name="login"),
    path('logout/', views.logout_view, name='logout'),
    path('shipments/change-password/', views.change_password, name='change_password'),

    path('fixed-cost-config/', views.fixed_cost_config_view, name='fixed_cost_config'),



    path('shipment/<int:shipment_id>/undo/', views.shipment_undo, name='shipment_undo'),


    path('form/', views.shipment_form, name='shipment_form'),  # New shipment
    path('form/<int:shipment_id>/', views.shipment_form, name='shipment_edit'),  # Edit existing shipment
    path('finalize/<int:shipment_id>/', views.shipment_finalize, name='shipment_finalize'),  # Finalize shipment
    path('list/', views.shipment_list, name='shipment_list'),  # View all shipments
    path('view/<int:shipment_id>/', views.shipment_view, name='shipment_view'),  # View single shipment details
    path('dashboard/', views.dashboard, name='dashboard'),


    # Autocomplete suggestion endpoints
    path('trip-suggestions/', views.shipment_trip_suggestions, name='shipment_trip_suggestions'),
    path('vehicle-suggestions/', views.shipment_vehicle_suggestions, name='shipment_vehicle_suggestions'),
    
    path('vehicle-maintenance/', views.manage_vehicle_maintenance, name='manage_vehicle_maintenance'),


    path('export/', views.shipment_export, name='shipment_export'),

    # Delete shipment (only for New status)
    path('delete/<int:pk>/', views.shipment_delete, name='shipment_delete'),

        path('reset_admin/', views.reset_admin, name='reset_admin'),
            path('create_admin/', views.create_admin, name='create_admin'),


]

