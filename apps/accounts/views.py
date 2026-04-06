"""
Accounts App — Serializers & Views
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Handles: Register, Login (JWT), Logout, Profile
"""
# ─── serializers.py ──────────────────────────────────────────────────────────

from rest_framework import serializers
from django.contrib.auth import authenticate
from apps.accounts.models import User
from security.middleware import InputSanitizer, JWTUtils

sanitizer = InputSanitizer()


class RegisterSerializer(serializers.ModelSerializer):
    """Validate and create a new customer account."""

    password  = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, label='Confirm password')

    class Meta:
        model  = User
        fields = ['email', 'first_name', 'last_name', 'phone', 'password', 'password2']

    def validate(self, data):
        # Check passwords match
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password2': 'Passwords do not match.'})

        # Run input sanitization (SQL injection / XSS check)
        sanitizer.validate({
            'email':      data.get('email', ''),
            'first_name': data.get('first_name', ''),
            'last_name':  data.get('last_name', ''),
        })
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        # create_user hashes the password with bcrypt automatically
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    """Authenticate user and return JWT tokens."""

    email    = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError('Invalid email or password.')
        if not user.is_active:
            raise serializers.ValidationError('Account is deactivated.')
        data['user'] = user
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    """Read/update user profile."""

    full_name = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name',
                  'phone', 'role', 'loyalty_points', 'date_joined']
        read_only_fields = ['id', 'email', 'role', 'loyalty_points', 'date_joined']

    def get_full_name(self, obj):
        return obj.get_full_name()


# ─── views.py ─────────────────────────────────────────────────────────────────

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated


class RegisterView(APIView):
    """
    POST /api/auth/register
    Body: { email, first_name, last_name, phone, password, password2 }
    Returns: JWT tokens + user info
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user   = serializer.save()
            tokens = JWTUtils.generate_tokens(user)
            return Response({
                'message': 'Account created successfully! Welcome to BrewMate.',
                **tokens
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """
    POST /api/auth/login
    Body: { email, password }
    Returns: { access, refresh, user: { id, email, name, role, loyalty_points } }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user   = serializer.validated_data['user']
            tokens = JWTUtils.generate_tokens(user)
            return Response(tokens, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    """
    POST /api/auth/logout
    Blacklists the refresh token — user must login again.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'error': 'Refresh token required.'}, status=400)

        success = JWTUtils.blacklist_token(refresh_token)
        if success:
            return Response({'message': 'Logged out successfully.'})
        return Response({'error': 'Invalid token.'}, status=400)


class ProfileView(APIView):
    """
    GET  /api/auth/profile  — view own profile
    PUT  /api/auth/profile  — update name/phone
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = UserProfileSerializer(
            request.user, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)
