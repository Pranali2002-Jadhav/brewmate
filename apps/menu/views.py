"""
Menu App — Complete Menu Management
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Models:   Category, MenuItem, Customization
Views:    Public menu listing, Admin CRUD
"""
# ═══════════════════════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════════════════════
from django.db import models
from django.core.cache import cache


class Category(models.Model):
    """
    DB Table: menu_category
    Examples: Hot Coffee, Cold Coffee, Tea, Snacks, Desserts
    """
    name        = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    icon        = models.CharField(max_length=10, blank=True, help_text="Emoji icon")
    order       = models.PositiveIntegerField(default=0, help_text="Display order")
    is_active   = models.BooleanField(default=True)

    class Meta:
        db_table  = 'menu_category'
        ordering  = ['order', 'name']

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    """
    DB Table: menu_item
    ┌─────────────────────┬────────────────────────────────────────────┐
    │ Field               │ Description                                │
    ├─────────────────────┼────────────────────────────────────────────┤
    │ category            │ FK → Category                              │
    │ name                │ "Cappuccino", "Cold Brew"                  │
    │ price               │ Base price in INR                          │
    │ customization_opts  │ JSON: sizes, milk options, add-ons         │
    │ is_available        │ Staff can toggle off when item runs out    │
    └─────────────────────┴────────────────────────────────────────────┘
    """
    category             = models.ForeignKey(Category, on_delete=models.CASCADE,
                                             related_name='items')
    name                 = models.CharField(max_length=100)
    description          = models.TextField(blank=True)
    price                = models.DecimalField(max_digits=8, decimal_places=2)
    image                = models.ImageField(upload_to='menu/', blank=True, null=True)
    is_available         = models.BooleanField(default=True)
    is_featured          = models.BooleanField(default=False)
    preparation_time_min = models.PositiveIntegerField(default=5,
                           help_text="Minutes to prepare")

    # JSON field storing customization options
    # Example: {
    #   "sizes": [{"name": "Small", "extra_price": 0}, {"name": "Large", "extra_price": 30}],
    #   "milk":  ["Whole", "Skim", "Oat", "Almond"],
    #   "extras": [{"name": "Extra shot", "price": 20}, {"name": "Whipped cream", "price": 15}]
    # }
    customization_options = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'menu_item'
        ordering = ['category', 'name']
        indexes  = [
            models.Index(fields=['is_available']),
            models.Index(fields=['category', 'is_available']),
        ]

    def __str__(self):
        return f"{self.name} — ₹{self.price}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Invalidate menu cache when any item is updated
        cache.delete('menu:all')
        cache.delete(f'menu:category:{self.category_id}')


# ═══════════════════════════════════════════════════════════════════════════════
# SERIALIZERS
# ═══════════════════════════════════════════════════════════════════════════════
from rest_framework import serializers
from security.middleware import InputSanitizer

sanitizer = InputSanitizer()


class CategorySerializer(serializers.ModelSerializer):
    item_count = serializers.SerializerMethodField()

    class Meta:
        model  = Category
        fields = ['id', 'name', 'description', 'icon', 'order', 'item_count']

    def get_item_count(self, obj):
        return obj.items.filter(is_available=True).count()


class MenuItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model  = MenuItem
        fields = ['id', 'category', 'category_name', 'name', 'description',
                  'price', 'image', 'is_available', 'is_featured',
                  'preparation_time_min', 'customization_options']

    def validate(self, data):
        sanitizer.validate({
            'name':        data.get('name', ''),
            'description': data.get('description', ''),
        })
        return data


class MenuItemAdminSerializer(MenuItemSerializer):
    """Extended serializer for admin — includes timestamps."""
    class Meta(MenuItemSerializer.Meta):
        fields = MenuItemSerializer.Meta.fields + ['created_at', 'updated_at']


# ═══════════════════════════════════════════════════════════════════════════════
# VIEWS
# ═══════════════════════════════════════════════════════════════════════════════
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from security.middleware import IsAdminUser, IsStaff
from django.core.cache import cache


class MenuListView(APIView):
    """
    GET /api/menu/
    Returns full menu grouped by category.
    Result is cached in Redis for 5 minutes — menu doesn't change every minute.
    Public endpoint — no authentication needed.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        # Try Redis cache first (much faster than hitting the DB)
        cached_menu = cache.get('menu:all')
        if cached_menu:
            return Response({'from_cache': True, 'menu': cached_menu})

        categories = Category.objects.filter(is_active=True).prefetch_related(
            models.Prefetch(
                'items',
                queryset=MenuItem.objects.filter(is_available=True),
                to_attr='available_items'
            )
        )

        menu_data = []
        for cat in categories:
            items = MenuItemSerializer(cat.available_items, many=True).data
            if items:  # Only include categories that have items
                menu_data.append({
                    'category': CategorySerializer(cat).data,
                    'items': items
                })

        # Cache in Redis for 5 minutes
        cache.set('menu:all', menu_data, timeout=300)
        return Response({'from_cache': False, 'menu': menu_data})


class MenuItemDetailView(APIView):
    """
    GET /api/menu/<id>/  — single item details
    """
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            item = MenuItem.objects.get(pk=pk, is_available=True)
        except MenuItem.DoesNotExist:
            return Response({'error': 'Item not found.'}, status=404)
        return Response(MenuItemSerializer(item).data)


class MenuAdminView(APIView):
    """
    Admin endpoints to manage menu items.
    POST   /api/menu/admin/        — add new item
    PUT    /api/menu/admin/<id>/   — update item
    DELETE /api/menu/admin/<id>/   — remove item
    PATCH  /api/menu/admin/<id>/toggle/  — toggle availability
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = MenuItemAdminSerializer(data=request.data)
        if serializer.is_valid():
            item = serializer.save()
            return Response(MenuItemAdminSerializer(item).data, status=201)
        return Response(serializer.errors, status=400)

    def put(self, request, pk):
        try:
            item = MenuItem.objects.get(pk=pk)
        except MenuItem.DoesNotExist:
            return Response({'error': 'Item not found.'}, status=404)

        serializer = MenuItemAdminSerializer(item, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        try:
            item = MenuItem.objects.get(pk=pk)
            item.delete()
            return Response({'message': 'Item deleted.'}, status=204)
        except MenuItem.DoesNotExist:
            return Response({'error': 'Item not found.'}, status=404)


class ToggleAvailabilityView(APIView):
    """
    PATCH /api/menu/admin/<id>/toggle/
    Staff can quickly mark an item unavailable when it runs out.
    """
    permission_classes = [IsStaff]

    def patch(self, request, pk):
        try:
            item = MenuItem.objects.get(pk=pk)
            item.is_available = not item.is_available
            item.save()
            status_str = "available" if item.is_available else "unavailable"
            return Response({
                'message': f'{item.name} is now {status_str}.',
                'is_available': item.is_available
            })
        except MenuItem.DoesNotExist:
            return Response({'error': 'Item not found.'}, status=404)
