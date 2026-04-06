from django.core.management.base import BaseCommand
from django.utils.text import slugify
from coffee.models import (
    User, Category, Product, Inventory, ShopTable, LoyaltyAccount
)


class Command(BaseCommand):
    help = 'Seeds BrewMate with sample data — run after migrate'

    def handle(self, *args, **kwargs):
        self.stdout.write('\n🌱  Seeding BrewMate...\n')

        # ── Users ─────────────────────────────────────────────────
        USERS = [
            dict(email='admin@brewmate.com', password='admin123',
                 first_name='Admin',   last_name='User',
                 role='admin',   is_staff=True,  is_superuser=True),
            dict(email='staff@brewmate.com', password='staff123',
                 first_name='Kitchen', last_name='Staff',
                 role='staff',   is_staff=False, is_superuser=False),
            dict(email='demo@brewmate.com',  password='demo123',
                 first_name='Priya',   last_name='Sharma',
                 role='customer', is_staff=False, is_superuser=False),
            dict(email='rahul@brewmate.com', password='demo123',
                 first_name='Rahul',   last_name='Mehta',
                 role='customer', is_staff=False, is_superuser=False),
        ]
        for ud in USERS:
            if not User.objects.filter(email=ud['email']).exists():
                u = User.objects.create_user(
                    email=ud['email'],         password=ud['password'],
                    first_name=ud['first_name'], last_name=ud['last_name'],
                    role=ud['role'],
                    is_staff=ud['is_staff'],   is_superuser=ud['is_superuser'],
                )
                la, _ = LoyaltyAccount.objects.get_or_create(user=u)
                if ud['role'] == 'customer':
                    la.points       = 85
                    la.total_earned = 85
                    la.save()
        self.stdout.write(self.style.SUCCESS(f'✓ Users ready'))

        # ── Categories ────────────────────────────────────────────
        CATS = [
            ('Hot Coffee',  '☕', 1),
            ('Cold Coffee', '🧊', 2),
            ('Tea',         '🍵', 3),
            ('Snacks',      '🥐', 4),
            ('Desserts',    '🍰', 5),
            ('Smoothies',   '🥤', 6),
        ]
        for name, icon, order in CATS:
            Category.objects.get_or_create(
                name=name, defaults={'icon': icon, 'order': order}
            )
        self.stdout.write(self.style.SUCCESS(f'✓ {len(CATS)} categories ready'))

        # ── Products ──────────────────────────────────────────────
        hot     = Category.objects.get(name='Hot Coffee')
        cold    = Category.objects.get(name='Cold Coffee')
        tea     = Category.objects.get(name='Tea')
        snack   = Category.objects.get(name='Snacks')
        dessert = Category.objects.get(name='Desserts')
        smooth  = Category.objects.get(name='Smoothies')

        PRODUCTS = [
            # (cat, name, description, price, featured, prep, calories)
            (hot,     'Espresso',         'Bold single shot of premium espresso',          80,  True,  4,   5),
            (hot,     'Cappuccino',        'Espresso with velvety steamed milk foam',       120, True,  6, 120),
            (hot,     'Latte',            'Smooth espresso with creamy steamed milk',       130, False, 6, 150),
            (hot,     'Flat White',       'Double espresso with silky microfoam',           140, True,  6, 130),
            (hot,     'Americano',        'Espresso diluted with hot water',                100, False, 5,  10),
            (hot,     'Mocha',            'Espresso with chocolate and steamed milk',       150, False, 7, 250),
            (cold,    'Cold Brew',        '12-hour slow-brewed cold coffee',                160, True,  2,   5),
            (cold,    'Iced Latte',       'Espresso over ice with cold milk',               150, True,  4, 140),
            (cold,    'Frappuccino',      'Blended iced coffee with whipped cream',         180, True,  8, 280),
            (cold,    'Iced Americano',   'Bold espresso over ice',                         120, False, 3,  10),
            (tea,     'Masala Chai',      'Aromatic Indian spiced tea with milk',            80, True,  7, 100),
            (tea,     'Green Tea',        'Refreshing Japanese green tea',                   70, False, 5,   0),
            (tea,     'Matcha Latte',     'Premium matcha with steamed milk',               160, True,  6, 180),
            (snack,   'Butter Croissant', 'Flaky golden French croissant',                  100, True,  2, 320),
            (snack,   'Banana Bread',     'Moist homemade banana bread',                     90, True,  1, 250),
            (snack,   'Club Sandwich',    'Triple-decker toasted sandwich',                  180, False, 8, 420),
            (dessert, 'Chocolate Cake',   'Rich dark chocolate fudge cake',                  120, True,  3, 450),
            (dessert, 'Cheesecake',       'Creamy New York-style cheesecake',                150, True,  3, 400),
            (smooth,  'Mango Smoothie',   'Fresh mango blended with yogurt and honey',       140, True,  5, 220),
            (smooth,  'Berry Blast',      'Mixed berry smoothie with chia seeds',            150, False, 5, 180),
        ]

        count = 0
        for cat, name, desc, price, featured, prep, cal in PRODUCTS:
            if not Product.objects.filter(name=name).exists():
                slug = slugify(name)
                base, n = slug, 1
                while Product.objects.filter(slug=slug).exists():
                    slug = f'{base}-{n}'
                    n += 1
                p = Product.objects.create(
                    category=cat, name=name, slug=slug,
                    description=desc, price=price,
                    is_featured=featured, prep_time=prep, calories=cal,
                )
                Inventory.objects.create(
                    product=p, stock_quantity=100, low_stock_alert=10
                )
                count += 1
        self.stdout.write(self.style.SUCCESS(f'✓ {count} products + inventory ready'))

        # ── Tables ────────────────────────────────────────────────
        TABLES = [(1,2),(2,2),(3,4),(4,4),(5,6),(6,6),(7,8),(8,2),(9,4),(10,4)]
        for num, cap in TABLES:
            ShopTable.objects.get_or_create(
                number=num, defaults={'capacity': cap}
            )
        self.stdout.write(self.style.SUCCESS(f'✓ {len(TABLES)} tables ready'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('━' * 52))
        self.stdout.write(self.style.SUCCESS('✅  Seeding complete!'))
        self.stdout.write(self.style.SUCCESS(''))
        self.stdout.write(self.style.SUCCESS('  🔴 Admin    admin@brewmate.com  / admin123'))
        self.stdout.write(self.style.SUCCESS('  🟡 Staff    staff@brewmate.com  / staff123'))
        self.stdout.write(self.style.SUCCESS('  🟢 Customer demo@brewmate.com   / demo123'))
        self.stdout.write(self.style.SUCCESS('  🟢 Customer rahul@brewmate.com  / demo123'))
        self.stdout.write(self.style.SUCCESS(''))
        self.stdout.write(self.style.SUCCESS('  python manage.py runserver'))
        self.stdout.write(self.style.SUCCESS('  Open: http://127.0.0.1:8000'))
        self.stdout.write(self.style.SUCCESS('━' * 52))
