# attendance/forms.py
from django import forms
from django.contrib.auth.models import User
from .models import Payroll, Profile



class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput())
    password_confirm = forms.CharField(widget=forms.PasswordInput(), label="Confirm Password")
    employee_id = forms.CharField(max_length=50)

    class Meta:
        model = User
        fields = ['username', 'email']

    def clean_password_confirm(self):
        password = self.cleaned_data.get('password')
        password_confirm = self.cleaned_data.get('password_confirm')
        if password != password_confirm:
            raise forms.ValidationError("Passwords do not match.")
        return password_confirm

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            # Create a UserProfile object
            user_profile = Profile(user=user, employee_id=self.cleaned_data.get('employee_id'))
            user_profile.save()
        return user
    
class PayrollForm(forms.ModelForm):
    class Meta:
        model = Payroll
        fields = ['employee', 'pay_period_start', 'pay_period_end', 'basic_salary', 'deduction', 'total_amount']
        