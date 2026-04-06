"""
URL Files for All Apps
━━━━━━━━━━━━━━━━━━━━━
Save each section as the urls.py file in its respective app folder.
"""

# ════════════════════════════════════════
# apps/accounts/urls.py
# ════════════════════════════════════════
"""
from django.urls import path
from apps.accounts.views import RegisterView, LoginView, LogoutView, ProfileView

urlpatterns = [
    path('register/', RegisterView.as_view(),  name='register'),
    path('login/',    LoginView.as_view(),     name='login'),
    path('logout/',   LogoutView.as_view(),    name='logout'),
    path('profile/',  ProfileView.as_view(),   name='profile'),
]
"""

# ════════════════════════════════════════
# apps/menu/urls.py
# ════════════════════════════════════════
"""
from django.urls import path
from apps.menu.views import (
    MenuListView, MenuItemDetailView, MenuAdminView, ToggleAvailabilityView
)

urlpatterns = [
    path('',                        MenuListView.as_view(),         name='menu-list'),
    path('<int:pk>/',               MenuItemDetailView.as_view(),   name='menu-item-detail'),
    path('admin/',                  MenuAdminView.as_view(),        name='menu-admin'),
    path('admin/<int:pk>/',         MenuAdminView.as_view(),        name='menu-admin-detail'),
    path('admin/<int:pk>/toggle/',  ToggleAvailabilityView.as_view(), name='menu-toggle'),
]
"""

# ════════════════════════════════════════
# apps/orders/urls.py
# ════════════════════════════════════════
"""
from django.urls import path
from apps.orders.views import (
    PlaceOrderView, OrderDetailView, MyOrdersView,
    UpdateOrderStatusView, KitchenView
)

urlpatterns = [
    path('',               PlaceOrderView.as_view(),       name='place-order'),
    path('mine/',          MyOrdersView.as_view(),          name='my-orders'),
    path('kitchen/',       KitchenView.as_view(),           name='kitchen-view'),
    path('<int:pk>/',      OrderDetailView.as_view(),       name='order-detail'),
    path('<int:pk>/status/', UpdateOrderStatusView.as_view(), name='update-status'),
]
"""

# ════════════════════════════════════════
# apps/reservations/urls.py
# ════════════════════════════════════════
"""
from django.urls import path
from apps.combined_apps import ReservationView, CancelReservationView, AvailableSlotsView

urlpatterns = [
    path('',                      ReservationView.as_view(),       name='reservations'),
    path('<int:pk>/cancel/',       CancelReservationView.as_view(), name='cancel-reservation'),
    path('available/',             AvailableSlotsView.as_view(),    name='available-slots'),
]
"""

# ════════════════════════════════════════
# apps/loyalty/urls.py
# ════════════════════════════════════════
"""
from django.urls import path
from apps.combined_apps import LoyaltyDashboardView

urlpatterns = [
    path('', LoyaltyDashboardView.as_view(), name='loyalty-dashboard'),
]
"""

# ════════════════════════════════════════
# apps/notifications/urls.py
# ════════════════════════════════════════
"""
from django.urls import path

urlpatterns = []  # Notifications are triggered internally, no direct user endpoints
"""
