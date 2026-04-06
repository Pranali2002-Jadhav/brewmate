from rest_framework import serializers
from coffee.models import (
    User, Category, Product, Cart, CartItem,
    Order, OrderItem, Reservation, LoyaltyAccount,
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ['id', 'email', 'first_name', 'last_name', 'phone', 'role']
        read_only_fields = ['id', 'role']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model  = Category
        fields = ['id', 'name', 'icon', 'order']


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model  = Product
        fields = ['id', 'category', 'category_name', 'name', 'slug',
                  'description', 'price', 'is_available', 'is_featured',
                  'prep_time', 'calories']


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    subtotal     = serializers.SerializerMethodField()

    class Meta:
        model  = CartItem
        fields = ['id', 'product', 'product_name', 'quantity', 'notes', 'subtotal']

    def get_subtotal(self, obj):
        return str(obj.subtotal)


class CartSerializer(serializers.ModelSerializer):
    items      = CartItemSerializer(many=True, read_only=True)
    total      = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()

    class Meta:
        model  = Cart
        fields = ['id', 'items', 'total', 'item_count']

    def get_total(self, obj):      return str(obj.total)
    def get_item_count(self, obj): return obj.item_count


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    subtotal     = serializers.SerializerMethodField()

    class Meta:
        model  = OrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'unit_price', 'subtotal', 'notes']

    def get_subtotal(self, obj): return str(obj.subtotal)


class OrderSerializer(serializers.ModelSerializer):
    items        = OrderItemSerializer(many=True, read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    customer     = serializers.SerializerMethodField()

    class Meta:
        model  = Order
        fields = ['id', 'order_number', 'customer', 'order_type', 'status',
                  'status_label', 'items', 'subtotal', 'discount', 'total',
                  'special_notes', 'estimated_time', 'created_at']

    def get_customer(self, obj):
        return {'name': obj.user.get_full_name(), 'email': obj.user.email}


class ReservationSerializer(serializers.ModelSerializer):
    customer = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model  = Reservation
        fields = ['id', 'customer', 'date', 'time_slot', 'guests',
                  'status', 'confirmation_code', 'special_requests', 'created_at']
        read_only_fields = ['id', 'status', 'confirmation_code', 'created_at']


class LoyaltySerializer(serializers.ModelSerializer):
    can_redeem   = serializers.BooleanField(read_only=True)
    redeem_value = serializers.SerializerMethodField()

    class Meta:
        model  = LoyaltyAccount
        fields = ['points', 'total_earned', 'total_spent', 'can_redeem', 'redeem_value']

    def get_redeem_value(self, obj): return str(obj.redeem_value)
