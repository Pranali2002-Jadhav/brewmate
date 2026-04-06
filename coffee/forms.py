from django import forms
from django.contrib.auth.forms import AuthenticationForm
from coffee.models import User, Product, Category

FC = {'class': 'form-control'}


class RegisterForm(forms.ModelForm):
    password  = forms.CharField(
        widget=forms.PasswordInput(attrs={**FC, 'placeholder': 'Password (min 6 chars)'}),
        min_length=6
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={**FC, 'placeholder': 'Confirm Password'}),
        label='Confirm Password'
    )

    class Meta:
        model  = User
        fields = ['first_name', 'last_name', 'email', 'phone']
        widgets = {
            'first_name': forms.TextInput(attrs={**FC, 'placeholder': 'First Name'}),
            'last_name':  forms.TextInput(attrs={**FC, 'placeholder': 'Last Name'}),
            'email':      forms.EmailInput(attrs={**FC, 'placeholder': 'Email Address'}),
            'phone':      forms.TextInput(attrs={**FC, 'placeholder': 'Phone Number'}),
        }

    def clean(self):
        c = super().clean()
        if c.get('password') != c.get('password2'):
            raise forms.ValidationError('Passwords do not match.')
        return c

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={**FC, 'placeholder': 'Email Address', 'autofocus': True})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={**FC, 'placeholder': 'Password'})
    )


class ProfileForm(forms.ModelForm):
    class Meta:
        model  = User
        fields = ['first_name', 'last_name', 'phone', 'avatar']
        widgets = {
            'first_name': forms.TextInput(attrs=FC),
            'last_name':  forms.TextInput(attrs=FC),
            'phone':      forms.TextInput(attrs=FC),
        }


class CheckoutForm(forms.Form):
    ORDER_TYPES     = [('dine_in', 'Dine In'), ('takeaway', 'Takeaway'), ('delivery', 'Delivery')]
    PAYMENT_METHODS = [('cash', 'Cash'), ('card', 'Card'), ('upi', 'UPI')]

    order_type       = forms.ChoiceField(choices=ORDER_TYPES, widget=forms.RadioSelect())
    payment_method   = forms.ChoiceField(choices=PAYMENT_METHODS, widget=forms.RadioSelect())
    table_number     = forms.IntegerField(
        required=False, min_value=1,
        widget=forms.NumberInput(attrs={**FC, 'placeholder': 'Table number'})
    )
    use_loyalty      = forms.BooleanField(
        required=False, label='Redeem loyalty points (100 pts = ₹50 off)'
    )
    special_notes    = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={**FC, 'rows': 2, 'placeholder': 'Special instructions...'})
    )
    delivery_address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={**FC, 'rows': 2, 'placeholder': 'Delivery address...'})
    )


class ReservationForm(forms.Form):
    date             = forms.DateField(
        widget=forms.DateInput(attrs={**FC, 'type': 'date'})
    )
    time_slot        = forms.TimeField(
        widget=forms.TimeInput(attrs={**FC, 'type': 'time'})
    )
    guests           = forms.IntegerField(
        min_value=1, max_value=12,
        widget=forms.NumberInput(attrs={**FC, 'placeholder': 'Number of guests'})
    )
    special_requests = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={**FC, 'rows': 2, 'placeholder': 'Any requests?'})
    )


class ProductAdminForm(forms.ModelForm):
    class Meta:
        model  = Product
        fields = ['category', 'name', 'description', 'price', 'image',
                  'is_available', 'is_featured', 'prep_time', 'calories']
        widgets = {
            'category':    forms.Select(attrs=FC),
            'name':        forms.TextInput(attrs=FC),
            'description': forms.Textarea(attrs={**FC, 'rows': 3}),
            'price':       forms.NumberInput(attrs=FC),
            'prep_time':   forms.NumberInput(attrs=FC),
            'calories':    forms.NumberInput(attrs=FC),
        }
