from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from .models import Team, UserRole

User = get_user_model()
INPUT = 'w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
AVATAR = forms.FileInput(attrs={'class': INPUT, 'accept': 'image/*'})


class UserCreateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': INPUT}), label='Password')

    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'email', 'employee_id',
            'designation', 'department', 'role', 'team', 'manager',
            'mobile_number', 'status', 'avatar',
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': INPUT}),
            'first_name': forms.TextInput(attrs={'class': INPUT}),
            'last_name': forms.TextInput(attrs={'class': INPUT}),
            'email': forms.EmailInput(attrs={'class': INPUT}),
            'employee_id': forms.TextInput(attrs={'class': INPUT}),
            'designation': forms.TextInput(attrs={'class': INPUT}),
            'department': forms.TextInput(attrs={'class': INPUT}),
            'role': forms.Select(attrs={'class': INPUT}),
            'team': forms.Select(attrs={'class': INPUT}),
            'manager': forms.Select(attrs={'class': INPUT}),
            'mobile_number': forms.TextInput(attrs={'class': INPUT}),
            'status': forms.Select(attrs={'class': INPUT}),
            'avatar': AVATAR,
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data['password']
        validate_password(password, user)
        user.set_password(password)
        if user.role == UserRole.ADMIN:
            user.is_staff = True
        if commit:
            user.save()
        return user


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'employee_id',
            'designation', 'department', 'role', 'team', 'manager',
            'mobile_number', 'status', 'is_active', 'avatar',
        ]
        widgets = {f: forms.Select(attrs={'class': INPUT}) if f in ('role', 'team', 'manager', 'status') else forms.TextInput(attrs={'class': INPUT})
                   for f in ['first_name', 'last_name', 'email', 'employee_id', 'designation', 'department', 'mobile_number']}
        widgets.update({
            'role': forms.Select(attrs={'class': INPUT}),
            'team': forms.Select(attrs={'class': INPUT}),
            'manager': forms.Select(attrs={'class': INPUT}),
            'status': forms.Select(attrs={'class': INPUT}),
            'is_active': forms.CheckboxInput(attrs={'class': 'rounded'}),
            'avatar': AVATAR,
        })


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'mobile_number',
            'designation', 'department', 'avatar',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': INPUT}),
            'last_name': forms.TextInput(attrs={'class': INPUT}),
            'email': forms.EmailInput(attrs={'class': INPUT}),
            'mobile_number': forms.TextInput(attrs={'class': INPUT}),
            'designation': forms.TextInput(attrs={'class': INPUT}),
            'department': forms.TextInput(attrs={'class': INPUT}),
            'avatar': AVATAR,
        }
