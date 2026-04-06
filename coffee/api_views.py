from django.contrib.auth import authenticate
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from coffee.models import (
    User, Category, Product, Cart, CartItem,
    Order, Reservation, LoyaltyAccount,
)
from coffee.serializers import (
    UserSerializer, CategorySerializer, ProductSerializer,
    CartSerializer, OrderSerializer, ReservationSerializer, LoyaltySerializer,
)
from security.middleware import IsCustomerOrAbove, IsStaffOrAdmin


@api_view(['POST'])
@permission_classes([AllowAny])
def api_register(request):
    email      = request.data.get('email', '').strip()
    password   = request.data.get('password', '')
    first_name = request.data.get('first_name', '')
    if not email or not password:
        return Response({'error': 'Email and password required.'}, status=400)
    if User.objects.filter(email=email).exists():
        return Response({'error': 'Email already registered.'}, status=400)
    user = User.objects.create_user(
        email=email, password=password, first_name=first_name
    )
    LoyaltyAccount.objects.get_or_create(user=user)
    ref = RefreshToken.for_user(user)
    ref['role'] = user.role
    return Response({
        'access':  str(ref.access_token),
        'refresh': str(ref),
        'user':    UserSerializer(user).data,
    }, status=201)


@api_view(['POST'])
@permission_classes([AllowAny])
def api_login(request):
    user = authenticate(
        username=request.data.get('email', ''),
        password=request.data.get('password', '')
    )
    if not user:
        return Response({'error': 'Invalid credentials.'}, status=401)
    ref = RefreshToken.for_user(user)
    ref['role'] = user.role
    return Response({
        'access':  str(ref.access_token),
        'refresh': str(ref),
        'user':    UserSerializer(user).data,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def api_categories(request):
    cats = Category.objects.filter(is_active=True)
    return Response(CategorySerializer(cats, many=True).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def api_products(request):
    qs = Product.objects.filter(is_available=True).select_related('category')
    if request.GET.get('category'):
        qs = qs.filter(category_id=request.GET['category'])
    if request.GET.get('q'):
        qs = qs.filter(name__icontains=request.GET['q'])
    return Response(ProductSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def api_product_detail(request, pk):
    try:
        p = Product.objects.get(pk=pk, is_available=True)
    except Product.DoesNotExist:
        return Response({'error': 'Not found.'}, status=404)
    return Response(ProductSerializer(p).data)


@api_view(['GET'])
@permission_classes([IsCustomerOrAbove])
def api_cart(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    return Response(CartSerializer(cart).data)


@api_view(['POST'])
@permission_classes([IsCustomerOrAbove])
def api_add_to_cart(request):
    try:
        product = Product.objects.get(
            pk=request.data.get('product_id'), is_available=True
        )
    except Product.DoesNotExist:
        return Response({'error': 'Product not available.'}, status=404)
    qty  = int(request.data.get('quantity', 1))
    cart, _ = Cart.objects.get_or_create(user=request.user)
    item, created = CartItem.objects.get_or_create(
        cart=cart, product=product, defaults={'quantity': qty}
    )
    if not created:
        item.quantity += qty
        item.save()
    return Response(CartSerializer(cart).data)


@api_view(['GET'])
@permission_classes([IsCustomerOrAbove])
def api_my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return Response(OrderSerializer(orders, many=True).data)


@api_view(['GET'])
@permission_classes([IsCustomerOrAbove])
def api_order_detail(request, pk):
    try:
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return Response({'error': 'Not found.'}, status=404)
    if request.user.role == 'customer' and order.user != request.user:
        return Response({'error': 'Forbidden.'}, status=403)
    return Response(OrderSerializer(order).data)


@api_view(['GET'])
@permission_classes([IsStaffOrAdmin])
def api_all_orders(request):
    qs = Order.objects.select_related('user').order_by('-created_at')
    if request.GET.get('status'):
        qs = qs.filter(status=request.GET['status'])
    return Response(OrderSerializer(qs, many=True).data)


@api_view(['PATCH'])
@permission_classes([IsStaffOrAdmin])
def api_update_order_status(request, pk):
    try:
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return Response({'error': 'Not found.'}, status=404)
    new_status = request.data.get('status')
    VALID = {
        'pending':   ['confirmed', 'cancelled'],
        'confirmed': ['preparing', 'cancelled'],
        'preparing': ['ready'],
        'ready':     ['delivered'],
    }
    if new_status not in VALID.get(order.status, []):
        return Response(
            {'error': f'Cannot move from {order.status} to {new_status}.'},
            status=400
        )
    order.status = new_status
    order.save(update_fields=['status', 'updated_at'])
    return Response(OrderSerializer(order).data)


@api_view(['GET'])
@permission_classes([IsCustomerOrAbove])
def api_my_reservations(request):
    qs = Reservation.objects.filter(user=request.user).order_by('-created_at')
    return Response(ReservationSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsCustomerOrAbove])
def api_loyalty(request):
    la, _ = LoyaltyAccount.objects.get_or_create(user=request.user)
    return Response(LoyaltySerializer(la).data)
