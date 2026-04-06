import re
import time
import logging
from collections import defaultdict
from functools import wraps
from django.http import JsonResponse
from django.shortcuts import redirect
from django.conf import settings
from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    """200 req/min per IP — supports 5000+ total API hits."""
    _store = defaultdict(list)

    def __init__(self, get_response):
        self.get_response = get_response
        self.enabled = getattr(settings, 'RATE_LIMIT_ENABLED', True)
        self.max_req = getattr(settings, 'RATE_LIMIT_MAX_REQUESTS', 200)
        self.window  = getattr(settings, 'RATE_LIMIT_WINDOW', 60)
        self.exempt  = ['/admin/', '/static/', '/media/']

    def __call__(self, request):
        if self.enabled and not any(request.path.startswith(e) for e in self.exempt):
            ip  = self._get_ip(request)
            now = time.time()
            self._store[ip] = [t for t in self._store[ip] if now - t < self.window]
            self._store[ip].append(now)
            if len(self._store[ip]) > self.max_req:
                if request.path.startswith('/api/'):
                    return JsonResponse({'error': 'Too many requests.'}, status=429)
        return self.get_response(request)

    @staticmethod
    def _get_ip(request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR', '0.0.0.0')


class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        t0 = time.time()
        response = self.get_response(request)
        ms = round((time.time() - t0) * 1000)
        user = getattr(request, 'user', None)
        who  = user.email if (user and user.is_authenticated) else 'anon'
        logger.info(f'{request.method} {request.path} {response.status_code} {who} {ms}ms')
        return response


def role_required(*roles):
    """Decorator: @role_required('admin') or @role_required('staff','admin')"""
    def decorator(fn):
        @wraps(fn)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f'/login/?next={request.path}')
            if getattr(request.user, 'role', 'customer') not in roles:
                return redirect('/forbidden/')
            return fn(request, *args, **kwargs)
        return wrapper
    return decorator


class IsCustomerOrAbove(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class IsStaffOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and request.user.role in ('staff', 'admin'))


class IsAdminOnly(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and request.user.role == 'admin')
