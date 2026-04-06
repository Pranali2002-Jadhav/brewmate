"""
BrewMate Models
All fields have explicit defaults — zero migration prompts guaranteed.
"""
import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser, BaseUserManager, PermissionsMixin
)
from django.utils import timezone
from django.utils.text import slugify


# ─────────────────────────────────────────────────────────────────
# USER  (custom auth)
# ─────────────────────────────────────────────────────────────────
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError('Email required.')
        email = self.normalize_email(email)
        extra.setdefault('role', 'customer')
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.update({'role': 'admin', 'is_staff': True, 'is_superuser': True})
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    ROLES = [
        ('customer', 'Customer'),
        ('staff',    'Staff'),
        ('admin',    'Admin'),
    ]

    email       = models.EmailField(unique=True, db_index=True)
    first_name  = models.CharField(max_length=50, default='')
    last_name   = models.CharField(max_length=50, blank=True, default='')
    phone       = models.CharField(max_length=15, blank=True, default='')
    role        = models.CharField(max_length=10, choices=ROLES,
                                   default='customer', db_index=True)
    # avatar is optional — no migration issues with null=True
    avatar      = models.ImageField(upload_to='avatars/',
                                    blank=True, null=True, default=None)
    is_active   = models.BooleanField(default=True)
    is_staff    = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['first_name']
    objects         = UserManager()

    class Meta:
        db_table = 'coffee_user'

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    def __str__(self):
        return f'{self.email} ({self.role})'

    @property
    def is_admin_user(self):    return self.role == 'admin'
    @property
    def is_staff_member(self):  return self.role in ('staff', 'admin')


# ─────────────────────────────────────────────────────────────────
# CATEGORY
# ─────────────────────────────────────────────────────────────────
class Category(models.Model):
    name      = models.CharField(max_length=50, unique=True)
    icon      = models.CharField(max_length=10, default='☕')
    order     = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table            = 'coffee_category'
        ordering            = ['order', 'name']
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name


# ─────────────────────────────────────────────────────────────────
# PRODUCT
# ─────────────────────────────────────────────────────────────────
class Product(models.Model):
    category    = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name='products'
    )
    name        = models.CharField(max_length=100, default='')
    slug        = models.SlugField(max_length=120, unique=True,
                                   blank=True, default='')
    description = models.TextField(blank=True, default='')
    price       = models.DecimalField(max_digits=8, decimal_places=2,
                                      default=Decimal('0.00'))
    # image is optional
    image       = models.ImageField(upload_to='products/',
                                    blank=True, null=True, default=None)
    is_available = models.BooleanField(default=True, db_index=True)
    is_featured  = models.BooleanField(default=False)
    prep_time    = models.PositiveIntegerField(default=5)
    # calories optional
    calories     = models.PositiveIntegerField(null=True, blank=True,
                                               default=None)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'coffee_product'
        ordering = ['category', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            n = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{n}'
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} — ₹{self.price}'


# ─────────────────────────────────────────────────────────────────
# INVENTORY  (OneToOne with Product)
# ─────────────────────────────────────────────────────────────────
class Inventory(models.Model):
    product         = models.OneToOneField(
        Product, on_delete=models.CASCADE, related_name='inventory'
    )
    stock_quantity  = models.PositiveIntegerField(default=100)
    low_stock_alert = models.PositiveIntegerField(default=10)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table            = 'coffee_inventory'
        verbose_name_plural = 'Inventories'

    def __str__(self):
        return f'{self.product.name}: {self.stock_quantity}'

    @property
    def is_low(self):
        return self.stock_quantity <= self.low_stock_alert

    def deduct(self, qty):
        if self.stock_quantity >= qty:
            self.stock_quantity -= qty
            self.save(update_fields=['stock_quantity', 'updated_at'])
            return True
        return False


# ─────────────────────────────────────────────────────────────────
# CART  (OneToOne with User)
# ─────────────────────────────────────────────────────────────────
class Cart(models.Model):
    user       = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='cart'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'coffee_cart'

    def __str__(self):
        return f'Cart — {self.user.email}'

    @property
    def total(self):
        return sum(i.subtotal for i in self.items.select_related('product').all())

    @property
    def item_count(self):
        result = self.items.aggregate(t=models.Sum('quantity'))['t']
        return result or 0


class CartItem(models.Model):
    cart     = models.ForeignKey(
        Cart, on_delete=models.CASCADE, related_name='items'
    )
    # product: NOT NULL, but we are in a fresh DB so no existing rows
    product  = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    notes    = models.CharField(max_length=200, blank=True, default='')

    class Meta:
        db_table        = 'coffee_cartitem'
        unique_together = ('cart', 'product')

    def __str__(self):
        return f'{self.quantity}x {self.product.name}'

    @property
    def subtotal(self):
        return self.product.price * self.quantity


# ─────────────────────────────────────────────────────────────────
# SHOP TABLES
# ─────────────────────────────────────────────────────────────────
class ShopTable(models.Model):
    number    = models.PositiveIntegerField(unique=True)
    capacity  = models.PositiveIntegerField(default=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'coffee_shoptable'
        ordering = ['number']

    def __str__(self):
        return f'Table {self.number} (seats {self.capacity})'


# ─────────────────────────────────────────────────────────────────
# ORDER
# ─────────────────────────────────────────────────────────────────
class Order(models.Model):
    STATUS = [
        ('pending',   'Pending'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('ready',     'Ready'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    ORDER_TYPE = [
        ('dine_in',  'Dine In'),
        ('takeaway', 'Takeaway'),
        ('delivery', 'Delivery'),
    ]

    order_number   = models.CharField(max_length=12, unique=True,
                                      blank=True, default='')
    user           = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='orders'
    )
    # table is optional (takeaway orders have no table)
    table          = models.ForeignKey(
        ShopTable, on_delete=models.SET_NULL,
        null=True, blank=True, default=None
    )
    order_type     = models.CharField(max_length=10, choices=ORDER_TYPE,
                                      default='dine_in')
    status         = models.CharField(max_length=15, choices=STATUS,
                                      default='pending', db_index=True)
    subtotal       = models.DecimalField(max_digits=10, decimal_places=2,
                                         default=Decimal('0.00'))
    discount       = models.DecimalField(max_digits=10, decimal_places=2,
                                         default=Decimal('0.00'))
    total          = models.DecimalField(max_digits=10, decimal_places=2,
                                         default=Decimal('0.00'))
    loyalty_used   = models.PositiveIntegerField(default=0)
    special_notes  = models.TextField(blank=True, default='')
    estimated_time = models.PositiveIntegerField(default=10)
    created_at     = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'coffee_order'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = 'BM' + uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Order {self.order_number}'


class OrderItem(models.Model):
    order      = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='items'
    )
    # product: NOT NULL, fresh DB has no existing rows
    product    = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity   = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2,
                                     default=Decimal('0.00'))
    notes      = models.CharField(max_length=200, blank=True, default='')

    class Meta:
        db_table = 'coffee_orderitem'

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f'{self.quantity}x {self.product.name}'


# ─────────────────────────────────────────────────────────────────
# PAYMENT  (OneToOne with Order)
# ─────────────────────────────────────────────────────────────────
class Payment(models.Model):
    METHOD = [
        ('cash',   'Cash on Delivery'),
        ('card',   'Credit/Debit Card'),
        ('upi',    'UPI'),
        ('wallet', 'Wallet'),
    ]
    STATUS = [
        ('pending',  'Pending'),
        ('paid',     'Paid'),
        ('failed',   'Failed'),
        ('refunded', 'Refunded'),
    ]

    order          = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name='payment'
    )
    method         = models.CharField(max_length=10, choices=METHOD,
                                      default='cash')
    status         = models.CharField(max_length=10, choices=STATUS,
                                      default='pending')
    amount         = models.DecimalField(max_digits=10, decimal_places=2,
                                         default=Decimal('0.00'))
    transaction_id = models.CharField(max_length=100, blank=True, default='')
    paid_at        = models.DateTimeField(null=True, blank=True, default=None)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'coffee_payment'

    def __str__(self):
        return f'Payment {self.order.order_number} — {self.status}'


# ─────────────────────────────────────────────────────────────────
# RESERVATION
# ─────────────────────────────────────────────────────────────────
class Reservation(models.Model):
    STATUS = [
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    user              = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='reservations'
    )
    table             = models.ForeignKey(
        ShopTable, on_delete=models.SET_NULL,
        null=True, blank=True, default=None
    )
    date              = models.DateField(db_index=True)
    time_slot         = models.TimeField()
    guests            = models.PositiveIntegerField(default=2)
    status            = models.CharField(max_length=15, choices=STATUS,
                                         default='confirmed')
    confirmation_code = models.CharField(max_length=8, unique=True,
                                         blank=True, default='')
    special_requests  = models.TextField(blank=True, default='')
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table        = 'coffee_reservation'
        ordering        = ['date', 'time_slot']
        unique_together = ('table', 'date', 'time_slot')

    def save(self, *args, **kwargs):
        if not self.confirmation_code:
            self.confirmation_code = uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Res {self.confirmation_code}'


# ─────────────────────────────────────────────────────────────────
# LOYALTY
# ─────────────────────────────────────────────────────────────────
class LoyaltyAccount(models.Model):
    user         = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='loyalty'
    )
    points       = models.PositiveIntegerField(default=0)
    total_earned = models.PositiveIntegerField(default=0)
    total_spent  = models.PositiveIntegerField(default=0)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'coffee_loyaltyaccount'

    def __str__(self):
        return f'{self.user.email}: {self.points} pts'

    @property
    def can_redeem(self):
        return self.points >= 100

    @property
    def redeem_value(self):
        return Decimal(str(self.points)) * Decimal('0.50')

    def add_points(self, pts, order=None, desc=''):
        self.points       += pts
        self.total_earned += pts
        self.save(update_fields=['points', 'total_earned', 'updated_at'])
        LoyaltyTransaction.objects.create(
            account=self, order=order, tx_type='earn',
            points=pts,
            description=desc or f'+{pts} pts earned',
        )

    def redeem_points(self, pts, order=None):
        if self.points >= pts:
            self.points      -= pts
            self.total_spent += pts
            self.save(update_fields=['points', 'total_spent', 'updated_at'])
            LoyaltyTransaction.objects.create(
                account=self, order=order, tx_type='redeem',
                points=-pts,
                description=f'-{pts} pts redeemed',
            )
            return True
        return False


class LoyaltyTransaction(models.Model):
    TX_TYPE = [('earn', 'Earned'), ('redeem', 'Redeemed')]

    # null=True so Django never asks for a default on existing rows
    account     = models.ForeignKey(
        LoyaltyAccount, on_delete=models.CASCADE,
        related_name='transactions',
        null=True, blank=True, default=None,
    )
    order       = models.ForeignKey(
        Order, on_delete=models.SET_NULL,
        null=True, blank=True, default=None,
    )
    tx_type     = models.CharField(max_length=10, choices=TX_TYPE, default='earn')
    points      = models.IntegerField(default=0)
    description = models.CharField(max_length=200, blank=True, default='')
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'coffee_loyaltytx'
        ordering = ['-created_at']

    def __str__(self):
        who = self.account.user.email if self.account else '?'
        return f'{who}: {self.points} ({self.tx_type})'


# ─────────────────────────────────────────────────────────────────
# NOTIFICATION
# ─────────────────────────────────────────────────────────────────
class Notification(models.Model):
    NOTIF_TYPE = [
        ('order',       'Order Update'),
        ('reservation', 'Reservation'),
        ('loyalty',     'Loyalty Points'),
        ('system',      'System'),
    ]

    user       = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='notifications'
    )
    notif_type = models.CharField(max_length=15, choices=NOTIF_TYPE,
                                  default='system')
    title      = models.CharField(max_length=100, default='')
    message    = models.TextField(default='')
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'coffee_notification'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.email}: {self.title}'

    @staticmethod
    def send(user, title, message, notif_type='system'):
        return Notification.objects.create(
            user=user, title=title,
            message=message, notif_type=notif_type,
        )
