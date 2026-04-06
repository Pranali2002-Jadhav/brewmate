from django.urls import path
from coffee import views

urlpatterns = [
    # Public
    path('',                               views.home_view,             name='home'),
    path('about/',                         views.about_view,            name='about'),
    path('menu/',                          views.menu_view,             name='menu'),
    path('menu/<slug:slug>/',              views.product_detail_view,   name='product_detail'),
    path('forbidden/',                     views.forbidden_view,        name='forbidden'),
    # Accounts
    path('register/',                      views.register_view,         name='register'),
    path('login/',                         views.login_view,            name='login'),
    path('logout/',                        views.logout_view,           name='logout'),
    path('dashboard/',                     views.dashboard_view,        name='dashboard'),
    path('profile/',                       views.profile_view,          name='profile'),
    # Cart
    path('cart/',                          views.cart_view,             name='cart'),
    path('cart/add/<int:product_id>/',     views.add_to_cart,           name='add_to_cart'),
    path('cart/update/<int:item_id>/',     views.update_cart,           name='update_cart'),
    path('cart/remove/<int:item_id>/',     views.remove_from_cart,      name='remove_from_cart'),
    path('cart/clear/',                    views.clear_cart,            name='clear_cart'),
    path('checkout/',                      views.checkout_view,         name='checkout'),
    # Orders
    path('orders/',                        views.my_orders_view,        name='my_orders'),
    path('orders/<int:pk>/',               views.order_detail_view,     name='order_detail'),
    # Reservations
    path('reservations/',                  views.reservation_view,      name='reservation'),
    path('reservations/<int:pk>/cancel/',  views.cancel_reservation,    name='cancel_reservation'),
    # Loyalty
    path('loyalty/',                       views.loyalty_view,          name='loyalty'),
    # Notifications
    path('notifications/',                 views.notifications_view,    name='notifications'),
    path('notifications/<int:pk>/read/',   views.mark_read,             name='mark_read'),
    # Staff
    path('staff/',                         views.staff_home,            name='staff_home'),
    path('staff/orders/',                  views.staff_orders_view,     name='staff_orders'),
    path('staff/orders/<int:pk>/status/',  views.update_order_status,   name='update_order_status'),
    path('staff/inventory/',               views.inventory_view,        name='inventory'),
    path('staff/inventory/<int:pk>/update/', views.update_stock,        name='update_stock'),
    # Admin
    path('admin-panel/',                   views.admin_home,            name='admin_home'),
    path('admin-panel/products/',          views.admin_products,        name='admin_products'),
    path('admin-panel/products/add/',      views.admin_add_product,     name='admin_add_product'),
    path('admin-panel/products/<int:pk>/edit/',   views.admin_edit_product,   name='admin_edit_product'),
    path('admin-panel/products/<int:pk>/delete/', views.admin_delete_product, name='admin_delete_product'),
    path('admin-panel/users/',             views.admin_users,           name='admin_users'),
    path('admin-panel/reservations/',      views.admin_reservations,    name='admin_reservations'),
]
