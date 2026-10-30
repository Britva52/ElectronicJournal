from django import forms
from django.contrib.auth import get_user_model


class ProfileContactForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ('email',)
        labels = {'email': 'Электронная почта'}
        widgets = {'email': forms.EmailInput(attrs={'class': 'form-control', 'autocomplete': 'email'})}
