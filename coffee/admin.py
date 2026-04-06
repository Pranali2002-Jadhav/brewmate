from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from coffee.models import (
    User, Category, Product, Inventory, Cart, CartItem,
    Order, OrderItem, Payment, ShopTable, Reservation,
    LoyaltyAccount, LoyaltyTransaction, Notification,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display  = ('email', 'first_name', 'role', 'is_active', 'date_joined')
    list_filter   = ('role', 'is_active')
    search_fields = ('email', 'first_name', 'last_name')
    ordering      = ('-date_joined',)
    fieldsets = (
        (None,       {'fields': ('email', 'password')}),
        ('Personal', {'fields': ('first_name', 'last_name', 'phone', 'avatar')}),
        ('Role',     {'fields': ('role',)}),
        ('Perms',    {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )
    add_fieldsets = ((None, {
        'classes': ('wide',),
        'fields': ('email', 'first_name', 'role', 'password1', 'password2'),
    }),)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ('name', 'icon', 'order', 'is_active')
    list_editable = ('order', 'is_active')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display  = ('name', 'category', 'price', 'is_available', 'is_featured')
    list_editable = ('price', 'is_available', 'is_featured')
    search_fields = ('name',)
    list_filter   = ('category', 'is_available')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display  = ('product', 'stock_quantity', 'low_stock_alert', 'updated_at')
    list_editable = ('stock_quantity',)


class OrderItemInline(admin.TabularInline):
    model  = OrderItem
    extra  = 0
    fields = ('product', 'quantity', 'unit_price', 'notes')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display    = ('order_number', 'user', 'status', 'total', 'created_at')
    list_filter     = ('status', 'order_type')
    search_fields   = ('order_number', 'user__email')
    readonly_fields = ('order_number', 'created_at', 'updated_at')
    inlines         = [OrderItemInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'method', 'status', 'amount')
    list_filter  = ('method', 'status')


@admin.register(ShopTable)
class ShopTableAdmin(admin.ModelAdmin):
    list_display  = ('number', 'capacity', 'is_active')
    list_editable = ('capacity', 'is_active')


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display  = ('confirmation_code', 'user', 'table', 'date', 'time_slot', 'guests', 'status')
    list_filter   = ('status', 'date')
    search_fields = ('confirmation_code', 'user__email')


@admin.register(LoyaltyAccount)
class LoyaltyAccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'points', 'total_earned', 'total_spent')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'notif_type', 'is_read', 'created_at')
    list_filter  = ('notif_type', 'is_read')
