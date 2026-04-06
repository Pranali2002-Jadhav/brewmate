from coffee.models import Cart, Notification


def global_context(request):
    cart_count  = 0
    notif_count = 0
    if request.user.is_authenticated:
        try:
            cart_count = Cart.objects.get(user=request.user).item_count
        except Cart.DoesNotExist:
            pass
        notif_count = Notification.objects.filter(
            user=request.user, is_read=False
        ).count()
    return {'cart_count': cart_count, 'notif_count': notif_count}
