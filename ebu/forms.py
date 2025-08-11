# forms.py
from django import forms
from .models import User

class UserForm(forms.ModelForm):
    
    class Meta:
        model = User
        fields = ['admcode','lgName', 'emailId', 'phoneNumber']
        widgets = {
            'admcode': forms.HiddenInput(),
            'lgName': forms.TextInput(attrs={'class': 'form-control'}),
            'emailId': forms.EmailInput(attrs={'class': 'form-control'}),
            'phoneNumber': forms.TextInput(attrs={'class': 'form-control'}),
            
        }
