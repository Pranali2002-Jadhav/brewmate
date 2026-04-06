from django.urls import path
from coffee import api_views

urlpatterns = [
    path('auth/register/',          api_views.api_register,           name='api_register'),
    path('auth/login/',             api_views.api_login,               name='api_login'),
    path('categories/',             api_views.api_categories,          name='api_categories'),
    path('products/',               api_views.api_products,            name='api_products'),
    path('products/<int:pk>/',      api_views.api_product_detail,      name='api_product_detail'),
    path('cart/',                   api_views.api_cart,                name='api_cart'),
    path('cart/add/',               api_views.api_add_to_cart,         name='api_add_to_cart'),
    path('orders/',                 api_views.api_my_orders,           name='api_my_orders'),
    path('orders/all/',             api_views.api_all_orders,          name='api_all_orders'),
    path('orders/<int:pk>/',        api_views.api_order_detail,        name='api_order_detail'),
    path('orders/<int:pk>/status/', api_views.api_update_order_status, name='api_update_status'),
    path('reservations/',           api_views.api_my_reservations,     name='api_reservations'),
    path('loyalty/',                api_views.api_loyalty,             name='api_loyalty'),
]
