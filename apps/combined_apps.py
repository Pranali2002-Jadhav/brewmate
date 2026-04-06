"""
Reservations App, Loyalty App, Notifications App
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# ═══════════════════════════════════════════════════════════════════════════════
# RESERVATIONS APP
# ═══════════════════════════════════════════════════════════════════════════════

# --- models ---
from django.db import models
from apps.accounts.models import User
from apps.orders.views import Table
import uuid


class Reservation(models.Model):
    """
    DB Table: reservations_reservation
    Customer books a table in advance.
    """
    STATUS_CHOICES = [
        ('pending',   'Pending confirmation'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    user              = models.ForeignKey(User, on_delete=models.CASCADE,
                                          related_name='reservations')
    table             = models.ForeignKey(Table, on_delete=models.SET_NULL,
                                          null=True, blank=True)
    date              = models.DateField()
    time_slot         = models.TimeField()
    guests            = models.PositiveIntegerField(default=2)
    status            = models.CharField(max_length=15, choices=STATUS_CHOICES,
                                         default='pending')
    confirmation_code = models.CharField(max_length=8, unique=True, editable=False)
    special_requests  = models.TextField(blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.confirmation_code:
            self.confirmation_code = uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'reservations_reservation'
        indexes  = [
            models.Index(fields=['date', 'time_slot']),
            models.Index(fields=['user', 'status']),
        ]
        unique_together = ['table', 'date', 'time_slot']  # No double bookings!

    def __str__(self):
        return f"Reservation {self.confirmation_code} — {self.user.email} on {self.date}"


# --- serializers + views ---
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from security.middleware import IsCustomer, IsStaff
from django.utils import timezone
from datetime import datetime, timedelta


class ReservationSerializer(serializers.ModelSerializer):
    table_number = serializers.IntegerField(source='table.number', read_only=True)
    customer     = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model  = Reservation
        fields = ['id', 'customer', 'table_number', 'date', 'time_slot',
                  'guests', 'status', 'confirmation_code', 'special_requests', 'created_at']
        read_only_fields = ['id', 'status', 'confirmation_code', 'created_at']

    def validate_date(self, value):
        if value < timezone.now().date():
            raise serializers.ValidationError("Reservation date cannot be in the past.")
        return value

    def validate_guests(self, value):
        if value > 10:
            raise serializers.ValidationError("Maximum 10 guests per reservation.")
        return value


class ReservationView(APIView):
    """
    GET  /api/reservations/          — list my reservations
    POST /api/reservations/          — create reservation
    """
    permission_classes = [IsCustomer]

    def get(self, request):
        reservations = Reservation.objects.filter(
            user=request.user,
            date__gte=timezone.now().date()
        ).order_by('date', 'time_slot')
        return Response(ReservationSerializer(reservations, many=True).data)

    def post(self, request):
        serializer = ReservationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        data  = serializer.validated_data
        date  = data['date']
        time  = data['time_slot']
        seats = data['guests']

        # Find an available table that fits the group
        booked_tables = Reservation.objects.filter(
            date=date, time_slot=time, status__in=['pending', 'confirmed']
        ).values_list('table_id', flat=True)

        available_table = Table.objects.filter(
            capacity__gte=seats,
            is_active=True
        ).exclude(id__in=booked_tables).first()

        if not available_table:
            return Response({
                'error': 'No tables available for the selected date, time, and party size.'
            }, status=409)  # 409 Conflict

        reservation = Reservation.objects.create(
            user             = request.user,
            table            = available_table,
            date             = date,
            time_slot        = time,
            guests           = seats,
            status           = 'confirmed',  # Auto-confirm if table found
            special_requests = data.get('special_requests', '')
        )

        return Response({
            'message':           'Table reserved successfully!',
            'confirmation_code': reservation.confirmation_code,
            'table':             f"Table {available_table.number}",
            'reservation':       ReservationSerializer(reservation).data
        }, status=201)


class CancelReservationView(APIView):
    """DELETE /api/reservations/<id>/cancel/"""
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            res = Reservation.objects.get(pk=pk, user=request.user)
        except Reservation.DoesNotExist:
            return Response({'error': 'Reservation not found.'}, status=404)

        if res.status == 'cancelled':
            return Response({'error': 'Already cancelled.'}, status=400)

        res.status = 'cancelled'
        res.save(update_fields=['status'])
        return Response({'message': 'Reservation cancelled.'})


class AvailableSlotsView(APIView):
    """
    GET /api/reservations/available/?date=2024-03-15&guests=2
    Returns available time slots for a given date and party size.
    """
    permission_classes = [IsCustomer]

    def get(self, request):
        date_str = request.query_params.get('date')
        guests   = int(request.query_params.get('guests', 2))

        if not date_str:
            return Response({'error': 'date parameter required.'}, status=400)

        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)

        # Define available time slots (8 AM to 9 PM, every 30 min)
        all_slots = []
        start = datetime.combine(date, datetime.min.time().replace(hour=8))
        end   = datetime.combine(date, datetime.min.time().replace(hour=21))
        current = start
        while current < end:
            all_slots.append(current.time())
            current += timedelta(minutes=30)

        # Find which slots have at least one available table
        available_slots = []
        for slot in all_slots:
            booked = Reservation.objects.filter(
                date=date, time_slot=slot, status__in=['pending', 'confirmed']
            ).values_list('table_id', flat=True)

            has_table = Table.objects.filter(
                capacity__gte=guests, is_active=True
            ).exclude(id__in=booked).exists()

            if has_table:
                available_slots.append(slot.strftime('%H:%M'))

        return Response({'date': date_str, 'available_slots': available_slots})


# ═══════════════════════════════════════════════════════════════════════════════
# LOYALTY APP
# ═══════════════════════════════════════════════════════════════════════════════

class LoyaltyTransaction(models.Model):
    """
    DB Table: loyalty_transaction
    Full audit trail of every points earn/spend event.
    """
    user          = models.ForeignKey(User, on_delete=models.CASCADE,
                                      related_name='loyalty_transactions')
    order         = models.ForeignKey('orders.Order', on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name='loyalty_txns')
    points_earned = models.PositiveIntegerField(default=0)
    points_spent  = models.PositiveIntegerField(default=0)
    description   = models.CharField(max_length=200, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'loyalty_transaction'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email}: +{self.points_earned} / -{self.points_spent}"


class LoyaltyDashboardView(APIView):
    """
    GET /api/loyalty/
    Customer sees their points balance and transaction history.
    """
    permission_classes = [IsCustomer]

    def get(self, request):
        user         = request.user
        transactions = LoyaltyTransaction.objects.filter(user=user)[:20]

        history = [{
            'date':          txn.created_at.strftime('%d %b %Y'),
            'points_earned': txn.points_earned,
            'points_spent':  txn.points_spent,
            'description':   txn.description or f'Order #{txn.order_id}',
        } for txn in transactions]

        return Response({
            'current_balance':  user.loyalty_points,
            'can_redeem':       user.can_redeem_points,
            'redemption_value': f'₹{user.loyalty_points * 0.5:.0f}',
            'points_to_next_reward': max(0, 100 - user.loyalty_points),
            'history':          history,
            'rewards': {
                'free_coffee_at': 100,
                'points_per_rupee': 0.1,
                'rupee_per_point': 0.5,
            }
        })


# ═══════════════════════════════════════════════════════════════════════════════
# NOTIFICATIONS APP
# ═══════════════════════════════════════════════════════════════════════════════
import logging
from django.conf import settings
from django.core.mail import send_mail

notif_logger = logging.getLogger('notifications')


class NotificationService:
    """
    Sends SMS and email notifications.
    Used by: Order service (order ready), Reservation service (confirmed)

    In production, these calls should be made asynchronously via
    Celery background tasks to not block the HTTP response.
    """

    @staticmethod
    def send_order_confirmation(order):
        """Send SMS + email when order is placed."""
        message = (
            f"Hi {order.user.first_name}! Your BrewMate order #{order.id} "
            f"has been received. Estimated time: {order.estimated_time} mins. "
            f"Total: ₹{order.total}"
        )
        NotificationService._send_sms(order.user.phone, message)
        NotificationService._send_email(
            to_email=order.user.email,
            subject=f"BrewMate Order #{order.id} Confirmed",
            body=message
        )

    @staticmethod
    def send_order_ready(order):
        """Notify customer when order is ready for pickup."""
        message = (
            f"Hi {order.user.first_name}! Your order #{order.id} is READY! "
            f"Please collect at the counter. Enjoy your coffee!"
        )
        NotificationService._send_sms(order.user.phone, message)

    @staticmethod
    def send_reservation_confirmation(reservation):
        """Confirm table booking to customer."""
        message = (
            f"Hi {reservation.user.first_name}! Table reserved at BrewMate. "
            f"Date: {reservation.date}, Time: {reservation.time_slot.strftime('%I:%M %p')}, "
            f"Table: {reservation.table.number}, Guests: {reservation.guests}. "
            f"Code: {reservation.confirmation_code}"
        )
        NotificationService._send_sms(reservation.user.phone, message)

    @staticmethod
    def _send_sms(phone: str, message: str):
        """Send SMS via Twilio."""
        if not phone:
            return
        try:
            from twilio.rest import Client
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            client.messages.create(
                body=message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=f'+91{phone}'  # Indian numbers
            )
            notif_logger.info(f"SMS sent to {phone}")
        except Exception as e:
            notif_logger.error(f"SMS failed to {phone}: {e}")
            # Don't raise — notification failure should not fail the order

    @staticmethod
    def _send_email(to_email: str, subject: str, body: str):
        """Send email via Django's email backend (SMTP/SES)."""
        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                fail_silently=True,
            )
            notif_logger.info(f"Email sent to {to_email}")
        except Exception as e:
            notif_logger.error(f"Email failed to {to_email}: {e}")
