from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UsernameField

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'first_name',
            'last_name',
        ]
        labels = {
            'username':'Nome do usuário',
            'email':'Email',
            'first_name':'Primeiro nome',
            'last_name':'Sobrenome'
        }
        field_classes = {"username": UsernameField}


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'first_name',
            'last_name',
        ]
        labels = {
            'username':'Nome do usuário',
            'email':'Email',
            'first_name':'Primeiro nome',
            'last_name':'Sobrenome'
        }
