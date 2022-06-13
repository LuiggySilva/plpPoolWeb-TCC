from django.db import models

from django.contrib.auth.models import (
    AbstractUser, 
    AbstractBaseUser, 
    BaseUserManager
)

from django.db.models import signals
from django.template.defaultfilters import slugify
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import ugettext_lazy as _

# Create your models here.

class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """
    def create_user(self, email, password, **extra_fields):
        """
        Create and save a User with the given email and password.
        """
        if not email:
            raise ValueError(_('The Email must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = models.CharField(max_length=20)
    email = models.EmailField(_('email address'), unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=False)

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    labels = {
        'username':'Nome do usuário',   
        'email':'Email',
        'first_name':'Primeiro nome',
        'last_name':'Sobrenome'
    }

    def __str__(self):
        return f"{self.email}"


def user_pre_save(signal, instance, sender, **kwargs):
    instance.slug = slugify(instance.username)
signals.pre_save.connect(user_pre_save, sender=User)
