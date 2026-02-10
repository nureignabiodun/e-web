from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import *


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']


class LoginForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['phone_number', 'profile_picture']


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['full_name', 'phone_number', 'address_line1', 'address_line2',
                  'city', 'state', 'postal_code', 'country', 'is_default']
        widgets = {
            'is_default': forms.CheckboxInput(),
        }


class CheckoutForm(forms.Form):
    # Address selection or creation
    address = forms.IntegerField(required=False)

    # New address fields
    full_name = forms.CharField(max_length=100, required=False)
    phone_number = forms.CharField(max_length=15, required=False)
    address_line1 = forms.CharField(max_length=200, required=False)
    address_line2 = forms.CharField(max_length=200, required=False)
    city = forms.CharField(max_length=100, required=False)
    state = forms.CharField(max_length=100, required=False)
    postal_code = forms.CharField(max_length=10, required=False)
    country = forms.CharField(max_length=100, required=False, initial='Nigeria')

    # Payment method
    payment_method = forms.ChoiceField(
        choices=Order.PAYMENT_METHOD_CHOICES,
        widget=forms.RadioSelect
    )

    def clean(self):
        cleaned_data = super().clean()
        address_id = cleaned_data.get('address')

        if not address_id:
            # Validate new address fields
            required_fields = ['full_name', 'phone_number', 'address_line1',
                               'city', 'state', 'postal_code']

            for field in required_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, f'{field.replace("_", " ").title()} is required')

        return cleaned_data


class OrderStatusForm(forms.Form):
    STATUS_CHOICES = Order.STATUS_CHOICES

    status = forms.ChoiceField(choices=STATUS_CHOICES)
    description = forms.CharField(widget=forms.Textarea, required=False)
    location = forms.CharField(max_length=200, required=False)


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['category', 'name', 'slug', 'description', 'price', 'old_price',
                  'stock', 'available', 'image', 'image2', 'image3']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
        }
class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'slug', 'description', 'image']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

