from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.core.paginator import Paginator

from coffee.models import (
    User, Category, Product, Inventory,
    Cart, CartItem, Order, OrderItem, Payment,
    ShopTable, Reservation,
    LoyaltyAccount, LoyaltyTransaction, Notification,
)
from coffee.forms import (
    RegisterForm, LoginForm, ProfileForm,
    CheckoutForm, ReservationForm, ProductAdminForm,
)
from security.middleware import role_required


# ── Error pages ───────────────────────────────────────────────────
def error_403(request, exception=None):
    return render(request, 'errors/403.html', status=403)

def error_404(request, exception=None):
    return render(request, 'errors/404.html', status=404)

def error_500(request):
    return render(request, 'errors/500.html', status=500)

def forbidden_view(request):
    return render(request, 'errors/403.html', status=403)


# ── Public ────────────────────────────────────────────────────────
def home_view(request):
    featured   = Product.objects.filter(
        is_featured=True, is_available=True
    ).select_related('category')[:8]
    categories = Category.objects.filter(is_active=True)
    return render(request, 'coffee/home.html', {
        'featured': featured, 'categories': categories
    })

def about_view(request):
    return render(request, 'coffee/about.html')

def menu_view(request):
    categories = Category.objects.filter(is_active=True).prefetch_related('products')
    q      = request.GET.get('q', '').strip()
    cat_id = request.GET.get('category', '').strip()
    products = Product.objects.filter(is_available=True).select_related('category')
    if q:
        products = products.filter(
            Q(name__icontains=q) | Q(description__icontains=q)
        )
    if cat_id:
        products = products.filter(category_id=cat_id)
    return render(request, 'coffee/menu.html', {
        'categories':   categories,
        'products':     products,
        'q':            q,
        'selected_cat': cat_id,
    })

def product_detail_view(request, slug):
    product = get_object_or_404(Product, slug=slug, is_available=True)
    related = Product.objects.filter(
        category=product.category, is_available=True
    ).exclude(pk=product.pk)[:4]
    return render(request, 'coffee/product_detail.html', {
        'product': product, 'related': related
    })


# ── Accounts ──────────────────────────────────────────────────────
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        LoyaltyAccount.objects.get_or_create(user=user)
        login(request, user)
        Notification.send(
            user, 'Welcome to BrewMate! ☕',
            f'Hi {user.first_name}, your account is ready. Start ordering!',
            'system'
        )
        messages.success(request, f'Welcome, {user.first_name}! ☕')
        return redirect('dashboard')
    return render(request, 'coffee/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        messages.success(request, f'Welcome back, {user.first_name}! ☕')
        next_url = request.GET.get('next', '')
        return redirect(next_url) if next_url else redirect('dashboard')
    return render(request, 'coffee/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


@login_required
def dashboard_view(request):
    user = request.user
    if user.role == 'admin':
        return redirect('admin_home')
    if user.role == 'staff':
        return redirect('staff_home')
    # Customer
    orders       = Order.objects.filter(user=user).order_by('-created_at')[:5]
    loyalty, _   = LoyaltyAccount.objects.get_or_create(user=user)
    notifs       = Notification.objects.filter(user=user, is_read=False)[:5]
    reservations = Reservation.objects.filter(
        user=user, date__gte=timezone.now().date(), status='confirmed'
    ).order_by('date')[:3]
    return render(request, 'coffee/customer_dashboard.html', {
        'orders':       orders,
        'loyalty':      loyalty,
        'notifs':       notifs,
        'reservations': reservations,
    })


@login_required
def profile_view(request):
    form = ProfileForm(
        request.POST or None,
        request.FILES or None,
        instance=request.user
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profile updated.')
        return redirect('profile')
    return render(request, 'coffee/profile.html', {'form': form})


# ── Cart ──────────────────────────────────────────────────────────
def _get_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


@login_required
def cart_view(request):
    cart    = _get_cart(request.user)
    items   = cart.items.select_related('product').all()
    loyalty = LoyaltyAccount.objects.filter(user=request.user).first()
    return render(request, 'coffee/cart.html', {
        'cart':    cart,
        'items':   items,
        'loyalty': loyalty,
        'form':    CheckoutForm(),
    })


@login_required
@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_available=True)
    qty     = max(1, int(request.POST.get('quantity', 1)))
    notes   = request.POST.get('notes', '')
    cart    = _get_cart(request.user)
    item, created = CartItem.objects.get_or_create(
        cart=cart, product=product,
        defaults={'quantity': qty, 'notes': notes}
    )
    if not created:
        item.quantity += qty
        item.save(update_fields=['quantity'])
    messages.success(request, f'{product.name} added to cart! ☕')
    return redirect(request.POST.get('next', 'menu'))


@login_required
@require_POST
def update_cart(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)
    qty  = int(request.POST.get('quantity', 1))
    if qty < 1:
        item.delete()
        messages.info(request, 'Item removed.')
    else:
        item.quantity = qty
        item.save(update_fields=['quantity'])
    return redirect('cart')


@login_required
@require_POST
def remove_from_cart(request, item_id):
    get_object_or_404(CartItem, pk=item_id, cart__user=request.user).delete()
    messages.info(request, 'Item removed.')
    return redirect('cart')


@login_required
@require_POST
def clear_cart(request):
    _get_cart(request.user).items.all().delete()
    messages.info(request, 'Cart cleared.')
    return redirect('cart')


# ── Checkout / Orders ─────────────────────────────────────────────
@login_required
@require_POST
@transaction.atomic
def checkout_view(request):
    cart  = _get_cart(request.user)
    items = list(cart.items.select_related('product').all())
    if not items:
        messages.error(request, 'Your cart is empty.')
        return redirect('cart')

    form = CheckoutForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'Please fix form errors.')
        return redirect('cart')

    data        = form.cleaned_data
    use_loyalty = data.get('use_loyalty', False)

    subtotal = sum(i.subtotal for i in items)

    # Loyalty discount
    discount = Decimal('0')
    pts_used = 0
    loyalty  = LoyaltyAccount.objects.select_for_update().filter(
        user=request.user
    ).first()
    if use_loyalty and loyalty and loyalty.can_redeem:
        discount = min(loyalty.redeem_value, subtotal)
        pts_used = int(discount / Decimal('0.50'))

    total = subtotal - discount

    # Find table for dine-in
    table = None
    if data['order_type'] == 'dine_in' and data.get('table_number'):
        table = ShopTable.objects.filter(
            number=data['table_number'], is_active=True
        ).first()

    max_prep = max((i.product.prep_time for i in items), default=10)

    order = Order.objects.create(
        user=request.user, table=table,
        order_type=data['order_type'],
        subtotal=subtotal, discount=discount, total=total,
        loyalty_used=pts_used,
        special_notes=data.get('special_notes', ''),
        estimated_time=max_prep,
    )

    for item in items:
        OrderItem.objects.create(
            order=order, product=item.product,
            quantity=item.quantity, unit_price=item.product.price,
            notes=item.notes,
        )
        inv = getattr(item.product, 'inventory', None)
        if inv:
            inv.deduct(item.quantity)

    Payment.objects.create(
        order=order,
        method=data['payment_method'],
        status='paid' if data['payment_method'] != 'cash' else 'pending',
        amount=total,
        transaction_id='MOCK-' + order.order_number,
    )

    if pts_used > 0 and loyalty:
        loyalty.redeem_points(pts_used, order=order)

    pts_earned = int(total * Decimal('0.10'))
    if pts_earned > 0:
        la, _ = LoyaltyAccount.objects.get_or_create(user=request.user)
        la.add_points(pts_earned, order=order,
                      desc=f'Earned on {order.order_number}')

    cart.items.all().delete()

    Notification.send(
        request.user,
        f'Order {order.order_number} placed!',
        f'Confirmed. Est. time: {order.estimated_time} mins. ☕',
        'order',
    )

    messages.success(
        request,
        f'Order {order.order_number} placed! ☕  Est. {order.estimated_time} mins.'
    )
    return redirect('order_detail', pk=order.pk)


@login_required
def order_detail_view(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.user.role == 'customer' and order.user != request.user:
        return redirect('forbidden')
    return render(request, 'coffee/order_detail.html', {
        'order':   order,
        'payment': getattr(order, 'payment', None),
    })


@login_required
def my_orders_view(request):
    qs        = Order.objects.filter(user=request.user).select_related('table')
    paginator = Paginator(qs, 10)
    orders    = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'coffee/my_orders.html', {'orders': orders})


# ── Reservations ──────────────────────────────────────────────────
@login_required
def reservation_view(request):
    form   = ReservationForm(request.POST or None)
    my_res = Reservation.objects.filter(
        user=request.user,
        date__gte=timezone.now().date()
    ).order_by('date', 'time_slot')

    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        if d['date'] < timezone.now().date():
            messages.error(request, 'Date cannot be in the past.')
            return redirect('reservation')

        booked = Reservation.objects.filter(
            date=d['date'], time_slot=d['time_slot'], status='confirmed'
        ).values_list('table_id', flat=True)

        table = ShopTable.objects.filter(
            capacity__gte=d['guests'], is_active=True
        ).exclude(id__in=booked).first()

        if not table:
            messages.error(
                request, 'No tables available for that slot. Try another time.'
            )
        else:
            res = Reservation.objects.create(
                user=request.user, table=table,
                date=d['date'], time_slot=d['time_slot'],
                guests=d['guests'],
                special_requests=d.get('special_requests', ''),
            )
            Notification.send(
                request.user, 'Table Reserved! 🎉',
                f'Table {table.number} on {d["date"]}. Code: {res.confirmation_code}',
                'reservation',
            )
            messages.success(
                request, f'Reserved! Confirmation code: {res.confirmation_code}'
            )
            return redirect('reservation')

    return render(request, 'coffee/reservations.html', {
        'form': form, 'my_res': my_res
    })


@login_required
@require_POST
def cancel_reservation(request, pk):
    res = get_object_or_404(Reservation, pk=pk, user=request.user)
    res.status = 'cancelled'
    res.save(update_fields=['status'])
    messages.info(request, f'Reservation {res.confirmation_code} cancelled.')
    return redirect('reservation')


# ── Loyalty ───────────────────────────────────────────────────────
@login_required
def loyalty_view(request):
    loyalty, _ = LoyaltyAccount.objects.get_or_create(user=request.user)
    txns = LoyaltyTransaction.objects.filter(
        account=loyalty
    ).order_by('-created_at')[:20]
    return render(request, 'coffee/loyalty.html', {
        'loyalty': loyalty, 'transactions': txns
    })


# ── Notifications ─────────────────────────────────────────────────
@login_required
def notifications_view(request):
    notifs = Notification.objects.filter(user=request.user)
    Notification.objects.filter(
        user=request.user, is_read=False
    ).update(is_read=True)
    return render(request, 'coffee/notifications.html', {'notifs': notifs})


@login_required
@require_POST
def mark_read(request, pk):
    Notification.objects.filter(pk=pk, user=request.user).update(is_read=True)
    return JsonResponse({'ok': True})


# ── Staff / Kitchen ───────────────────────────────────────────────
@login_required
@role_required('staff', 'admin')
def staff_home(request):
    active_orders = Order.objects.filter(
        status__in=['pending', 'confirmed', 'preparing']
    ).prefetch_related('items__product').select_related('table', 'user').order_by('created_at')

    today         = timezone.now().date()
    today_qs      = Order.objects.filter(created_at__date=today)
    today_revenue = today_qs.aggregate(r=Sum('total'))['r'] or 0

    return render(request, 'coffee/staff_home.html', {
        'active_orders': active_orders,
        'today_orders':  today_qs.count(),
        'today_revenue': today_revenue,
    })


@login_required
@role_required('staff', 'admin')
@require_POST
def update_order_status(request, pk):
    order   = get_object_or_404(Order, pk=pk)
    new_st  = request.POST.get('status')
    VALID   = {
        'pending':   ['confirmed', 'cancelled'],
        'confirmed': ['preparing', 'cancelled'],
        'preparing': ['ready'],
        'ready':     ['delivered'],
    }
    if new_st in VALID.get(order.status, []):
        order.status = new_st
        order.save(update_fields=['status', 'updated_at'])
        Notification.send(
            order.user,
            f'Order {order.order_number} updated',
            f'Status: {order.get_status_display()} ☕',
            'order',
        )
        messages.success(request, f'Order #{order.id} → {new_st}')
    else:
        messages.error(request, f'Cannot move from {order.status} to {new_st}.')
    return redirect('staff_home')


@login_required
@role_required('staff', 'admin')
def staff_orders_view(request):
    status = request.GET.get('status', '')
    qs     = Order.objects.select_related('user', 'table').order_by('-created_at')
    if status:
        qs = qs.filter(status=status)
    paginator = Paginator(qs, 15)
    return render(request, 'coffee/staff_orders.html', {
        'orders':          paginator.get_page(request.GET.get('page', 1)),
        'selected_status': status,
        'status_choices':  Order.STATUS,
    })


@login_required
@role_required('staff', 'admin')
def inventory_view(request):
    inventories = Inventory.objects.select_related(
        'product__category'
    ).order_by('product__name')
    return render(request, 'coffee/inventory.html', {
        'inventories': inventories,
        'low_stock':   [i for i in inventories if i.is_low],
    })


@login_required
@role_required('staff', 'admin')
@require_POST
def update_stock(request, pk):
    inv = get_object_or_404(Inventory, pk=pk)
    inv.stock_quantity = max(0, int(request.POST.get('quantity', 0)))
    inv.save(update_fields=['stock_quantity', 'updated_at'])
    messages.success(request, f'Stock updated: {inv.product.name}.')
    return redirect('inventory')


# ── Admin Dashboard ───────────────────────────────────────────────
@login_required
@role_required('admin')
def admin_home(request):
    today  = timezone.now().date()
    orders = Order.objects.all()
    return render(request, 'coffee/admin_home.html', {
        'total_revenue': orders.aggregate(r=Sum('total'))['r'] or 0,
        'today_revenue': orders.filter(
            created_at__date=today).aggregate(r=Sum('total'))['r'] or 0,
        'total_orders':  orders.count(),
        'today_orders':  orders.filter(created_at__date=today).count(),
        'total_users':   User.objects.filter(role='customer').count(),
        'low_stock':     Inventory.objects.filter(stock_quantity__lte=10).count(),
        'recent_orders': orders.select_related('user').order_by('-created_at')[:10],
        'status_stats':  orders.values('status').annotate(count=Count('id')),
    })


@login_required
@role_required('admin')
def admin_products(request):
    products = Product.objects.select_related('category').order_by('category', 'name')
    return render(request, 'coffee/admin_products.html', {'products': products})


@login_required
@role_required('admin')
def admin_add_product(request):
    form = ProductAdminForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        product = form.save()
        Inventory.objects.get_or_create(
            product=product, defaults={'stock_quantity': 100}
        )
        messages.success(request, f'{product.name} added.')
        return redirect('admin_products')
    return render(request, 'coffee/admin_product_form.html', {
        'form': form, 'action': 'Add'
    })


@login_required
@role_required('admin')
def admin_edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form    = ProductAdminForm(
        request.POST or None, request.FILES or None, instance=product
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'{product.name} updated.')
        return redirect('admin_products')
    return render(request, 'coffee/admin_product_form.html', {
        'form': form, 'action': 'Edit', 'product': product
    })


@login_required
@role_required('admin')
@require_POST
def admin_delete_product(request, pk):
    get_object_or_404(Product, pk=pk).delete()
    messages.success(request, 'Product deleted.')
    return redirect('admin_products')


@login_required
@role_required('admin')
def admin_users(request):
    users = User.objects.prefetch_related('loyalty').order_by('-date_joined')
    return render(request, 'coffee/admin_users.html', {'users': users})


@login_required
@role_required('admin')
def admin_reservations(request):
    reservations = Reservation.objects.select_related(
        'user', 'table'
    ).order_by('-created_at')
    return render(request, 'coffee/admin_reservations.html', {
        'reservations': reservations
    })
