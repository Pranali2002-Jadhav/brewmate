"""
Orders App — The Heart of BrewMate
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Flow:
  Customer places order
    → Validate items & customizations
    → Calculate total
    → Process payment (Stripe/Razorpay)
    → Save order to DB
    → Award loyalty points
    → Notify kitchen (real-time)
    → Send SMS to customer
    → Customer tracks status live
"""
# ═══════════════════════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════════════════════
from django.db import models
from apps.accounts.models import User
from apps.menu.views import MenuItem


class Table(models.Model):
    """Physical tables in the coffee shop."""
    number   = models.PositiveIntegerField(unique=True)
    capacity = models.PositiveIntegerField(default=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'shop_table'
        ordering = ['number']

    def __str__(self):
        return f"Table {self.number} (seats {self.capacity})"


class Order(models.Model):
    """
    DB Table: orders_order
    ┌──────────────────┬──────────────────────────────────────────────┐
    │ Field            │ Description                                  │
    ├──────────────────┼──────────────────────────────────────────────┤
    │ user             │ FK → User (who placed the order)             │
    │ table            │ FK → Table (null for takeaway orders)        │
    │ status           │ pending → preparing → ready → delivered      │
    │ order_type       │ dine_in / takeaway / delivery                │
    │ subtotal         │ Sum of all items                             │
    │ discount         │ Loyalty points discount applied              │
    │ total            │ Final amount charged                         │
    │ payment_intent   │ Stripe payment reference ID                  │
    └──────────────────┴──────────────────────────────────────────────┘
    """
    STATUS_CHOICES = [
        ('pending',    'Pending'),
        ('confirmed',  'Confirmed'),
        ('preparing',  'Preparing'),
        ('ready',      'Ready for pickup'),
        ('delivered',  'Delivered'),
        ('cancelled',  'Cancelled'),
    ]

    ORDER_TYPE_CHOICES = [
        ('dine_in',  'Dine In'),
        ('takeaway', 'Takeaway'),
        ('delivery', 'Delivery'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('paid',      'Paid'),
        ('failed',    'Failed'),
        ('refunded',  'Refunded'),
    ]

    user              = models.ForeignKey(User, on_delete=models.PROTECT,
                                          related_name='orders')
    table             = models.ForeignKey(Table, on_delete=models.SET_NULL,
                                          null=True, blank=True, related_name='orders')
    status            = models.CharField(max_length=15, choices=STATUS_CHOICES,
                                         default='pending')
    order_type        = models.CharField(max_length=10, choices=ORDER_TYPE_CHOICES,
                                         default='dine_in')
    subtotal          = models.DecimalField(max_digits=10, decimal_places=2)
    loyalty_discount  = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total             = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status    = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES,
                                          default='pending')
    payment_intent_id = models.CharField(max_length=200, blank=True,
                                          help_text="Stripe payment intent ID")
    special_notes     = models.TextField(blank=True)
    estimated_time    = models.PositiveIntegerField(default=8,
                        help_text="Estimated preparation time in minutes")
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'orders_order'
        ordering = ['-created_at']
        indexes  = [
            models.Index(fields=['status']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Order #{self.id} — {self.user.email} — {self.status}"


class OrderItem(models.Model):
    """
    DB Table: orders_orderitem
    One row per item in an order.
    Stores customizations as JSON (size, milk type, extras).
    """
    order          = models.ForeignKey(Order, on_delete=models.CASCADE,
                                       related_name='items')
    menu_item      = models.ForeignKey(MenuItem, on_delete=models.PROTECT)
    quantity       = models.PositiveIntegerField(default=1)
    unit_price     = models.DecimalField(max_digits=8, decimal_places=2,
                     help_text="Price at time of order (menu price may change later)")
    customizations = models.JSONField(default=dict,
                     help_text='{"size": "Large", "milk": "Oat", "extras": ["Extra shot"]}')

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    class Meta:
        db_table = 'orders_orderitem'

    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name}"


# ═══════════════════════════════════════════════════════════════════════════════
# SERIALIZERS
# ═══════════════════════════════════════════════════════════════════════════════
from rest_framework import serializers
from decimal import Decimal


class OrderItemCreateSerializer(serializers.Serializer):
    """Validates each item in an incoming order request."""
    menu_item_id   = serializers.IntegerField()
    quantity       = serializers.IntegerField(min_value=1, max_value=20)
    customizations = serializers.DictField(required=False, default=dict)

    def validate_menu_item_id(self, value):
        try:
            item = MenuItem.objects.get(pk=value, is_available=True)
        except MenuItem.DoesNotExist:
            raise serializers.ValidationError(
                f"Menu item {value} is not available."
            )
        return value


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializes an order item for response."""
    item_name  = serializers.CharField(source='menu_item.name', read_only=True)
    line_total = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True, source='line_total'
    )

    class Meta:
        model  = OrderItem
        fields = ['id', 'item_name', 'quantity', 'unit_price',
                  'customizations', 'line_total']


class OrderCreateSerializer(serializers.Serializer):
    """Validates the entire order placement request."""
    items          = OrderItemCreateSerializer(many=True)
    order_type     = serializers.ChoiceField(
        choices=['dine_in', 'takeaway', 'delivery'], default='dine_in'
    )
    table_id       = serializers.IntegerField(required=False, allow_null=True)
    use_loyalty    = serializers.BooleanField(default=False,
                     help_text="Redeem loyalty points for discount")
    special_notes  = serializers.CharField(required=False, allow_blank=True, max_length=300)
    payment_method = serializers.ChoiceField(choices=['online', 'cash'], default='online')

    def validate(self, data):
        if data['order_type'] == 'dine_in' and not data.get('table_id'):
            raise serializers.ValidationError(
                {'table_id': 'Table number is required for dine-in orders.'}
            )
        if not data['items']:
            raise serializers.ValidationError({'items': 'Order must have at least one item.'})
        return data


class OrderSerializer(serializers.ModelSerializer):
    """Full order details for response."""
    items        = OrderItemSerializer(many=True, read_only=True)
    customer     = serializers.SerializerMethodField()
    table_number = serializers.SerializerMethodField()

    class Meta:
        model  = Order
        fields = ['id', 'customer', 'table_number', 'status', 'order_type',
                  'items', 'subtotal', 'loyalty_discount', 'total',
                  'payment_status', 'special_notes', 'estimated_time', 'created_at']

    def get_customer(self, obj):
        return {'name': obj.user.get_full_name(), 'phone': obj.user.phone}

    def get_table_number(self, obj):
        return obj.table.number if obj.table else None


# ═══════════════════════════════════════════════════════════════════════════════
# SERVICE LAYER — Business Logic
# ═══════════════════════════════════════════════════════════════════════════════
from decimal import Decimal
from django.db import transaction


class OrderService:
    """
    All business logic for order processing lives here — NOT in views.
    This keeps views thin and logic testable.
    """

    LOYALTY_POINTS_RATE  = Decimal('0.1')  # 10% of order value as points
    LOYALTY_REDEEM_VALUE = Decimal('0.50')  # ₹0.50 per point

    @classmethod
    @transaction.atomic  # If anything fails, entire order is rolled back
    def create_order(cls, user, validated_data) -> Order:
        """
        Create a complete order atomically.

        Steps:
        1. Calculate subtotal from items
        2. Apply loyalty discount if requested
        3. Create Order record
        4. Create OrderItem records
        5. Award loyalty points
        6. Send notifications (async)
        """
        items_data  = validated_data['items']
        use_loyalty = validated_data.get('use_loyalty', False)

        # ── Step 1: Calculate subtotal ────────────────────────────────────────
        subtotal = Decimal('0')
        item_objects = []

        for item_data in items_data:
            menu_item = MenuItem.objects.select_for_update().get(
                pk=item_data['menu_item_id']
            )
            unit_price = menu_item.price

            # Add prices for selected extras from customizations
            extras     = item_data.get('customizations', {}).get('extras', [])
            extra_cost = cls._calculate_extra_cost(menu_item, extras)
            unit_price += extra_cost

            line_total  = unit_price * item_data['quantity']
            subtotal   += line_total
            item_objects.append((menu_item, item_data, unit_price))

        # ── Step 2: Loyalty discount ──────────────────────────────────────────
        loyalty_discount = Decimal('0')
        if use_loyalty and user.can_redeem_points:
            # Calculate max discount from available points
            max_discount    = user.loyalty_points * cls.LOYALTY_REDEEM_VALUE
            # Discount cannot exceed order subtotal
            loyalty_discount = min(max_discount, subtotal)
            # Deduct points from user
            points_used  = int(loyalty_discount / cls.LOYALTY_REDEEM_VALUE)
            user.loyalty_points -= points_used
            user.save(update_fields=['loyalty_points'])

        total = subtotal - loyalty_discount

        # ── Step 3: Create Order ──────────────────────────────────────────────
        table = None
        if validated_data.get('table_id'):
            table = Table.objects.get(pk=validated_data['table_id'])

        order = Order.objects.create(
            user             = user,
            table            = table,
            order_type       = validated_data['order_type'],
            subtotal         = subtotal,
            loyalty_discount = loyalty_discount,
            total            = total,
            payment_status   = 'pending',
            special_notes    = validated_data.get('special_notes', ''),
            estimated_time   = cls._estimate_preparation_time(item_objects),
        )

        # ── Step 4: Create OrderItems ─────────────────────────────────────────
        order_items = [
            OrderItem(
                order          = order,
                menu_item      = menu_item,
                quantity       = item_data['quantity'],
                unit_price     = unit_price,
                customizations = item_data.get('customizations', {}),
            )
            for menu_item, item_data, unit_price in item_objects
        ]
        OrderItem.objects.bulk_create(order_items)

        # ── Step 5: Award loyalty points (earn while spending) ─────────────────
        points_earned = int(total * cls.LOYALTY_POINTS_RATE)
        if points_earned > 0:
            user.loyalty_points += points_earned
            user.save(update_fields=['loyalty_points'])

            # Create loyalty transaction record
            from apps.loyalty.views import LoyaltyTransaction
            LoyaltyTransaction.objects.create(
                user          = user,
                order         = order,
                points_earned = points_earned,
                points_spent  = int(loyalty_discount / cls.LOYALTY_REDEEM_VALUE),
            )

        return order

    @staticmethod
    def _calculate_extra_cost(menu_item, selected_extras: list) -> Decimal:
        """Calculate extra cost from selected add-ons."""
        options = menu_item.customization_options.get('extras', [])
        total   = Decimal('0')
        for extra in options:
            if extra['name'] in selected_extras:
                total += Decimal(str(extra.get('price', 0)))
        return total

    @staticmethod
    def _estimate_preparation_time(item_objects) -> int:
        """Estimate total prep time based on items ordered."""
        if not item_objects:
            return 5
        max_time = max(item[0].preparation_time_min for item in item_objects)
        # Multiple items = slightly longer (parallel preparation)
        return max_time + (2 if len(item_objects) > 2 else 0)

    @classmethod
    def update_status(cls, order, new_status: str, updated_by) -> Order:
        """Staff updates order status. Triggers notifications."""
        valid_transitions = {
            'pending':   ['confirmed', 'cancelled'],
            'confirmed': ['preparing', 'cancelled'],
            'preparing': ['ready'],
            'ready':     ['delivered'],
            'delivered': [],
            'cancelled': [],
        }
        if new_status not in valid_transitions.get(order.status, []):
            raise ValueError(
                f"Cannot move order from '{order.status}' to '{new_status}'."
            )

        order.status = new_status
        order.save(update_fields=['status', 'updated_at'])
        return order


# ═══════════════════════════════════════════════════════════════════════════════
# VIEWS
# ═══════════════════════════════════════════════════════════════════════════════
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from security.middleware import IsCustomer, IsStaff, IsOwnerOrStaff


class PlaceOrderView(APIView):
    """
    POST /api/orders/
    Customer places a new order.
    """
    permission_classes = [IsCustomer]

    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        try:
            order = OrderService.create_order(
                user=request.user,
                validated_data=serializer.validated_data
            )
            return Response({
                'message':        '✓ Order placed successfully!',
                'order_id':       order.id,
                'estimated_time': f'{order.estimated_time} minutes',
                'total':          str(order.total),
                'order':          OrderSerializer(order).data
            }, status=201)

        except Exception as e:
            return Response({'error': str(e)}, status=400)


class OrderDetailView(APIView):
    """
    GET /api/orders/<id>/   — track order status
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            order = Order.objects.prefetch_related('items__menu_item').get(pk=pk)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found.'}, status=404)

        # Customers can only see their own orders
        if request.user.role == 'customer' and order.user != request.user:
            return Response({'error': 'Access denied.'}, status=403)

        return Response(OrderSerializer(order).data)


class MyOrdersView(APIView):
    """
    GET /api/orders/mine/
    Customer's order history (latest first).
    """
    permission_classes = [IsCustomer]

    def get(self, request):
        orders = Order.objects.filter(user=request.user)\
                              .prefetch_related('items__menu_item')\
                              .order_by('-created_at')[:20]
        return Response(OrderSerializer(orders, many=True).data)


class UpdateOrderStatusView(APIView):
    """
    PATCH /api/orders/<id>/status/
    Staff updates order status: pending → preparing → ready → delivered
    """
    permission_classes = [IsStaff]

    def patch(self, request, pk):
        try:
            order      = Order.objects.get(pk=pk)
            new_status = request.data.get('status')

            if not new_status:
                return Response({'error': 'Status field is required.'}, status=400)

            order = OrderService.update_status(order, new_status, request.user)
            return Response({
                'message':    f'Order #{order.id} is now {order.get_status_display()}.',
                'order_id':   order.id,
                'new_status': order.status
            })
        except Order.DoesNotExist:
            return Response({'error': 'Order not found.'}, status=404)
        except ValueError as e:
            return Response({'error': str(e)}, status=400)


class KitchenView(APIView):
    """
    GET /api/orders/kitchen/
    Live view of all active orders for kitchen staff.
    Shows: pending, confirmed, preparing orders.
    """
    permission_classes = [IsStaff]

    def get(self, request):
        active_orders = Order.objects.filter(
            status__in=['pending', 'confirmed', 'preparing']
        ).prefetch_related('items__menu_item').select_related('table').order_by('created_at')

        return Response({
            'active_orders': len(active_orders),
            'orders': OrderSerializer(active_orders, many=True).data
        })
