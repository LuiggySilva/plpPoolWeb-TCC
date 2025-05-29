from django.contrib.auth.models import BaseUserManager

from questions.models import Period


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('O email é obrigatório')
        if not extra_fields.get('name'):
            raise ValueError('O nome é obrigatório')
        # Permitir superusuário sem período
        if not extra_fields.get('period') and not extra_fields.get('is_superuser'):
            raise ValueError('O período é obrigatório')
            
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('name', 'Super Usuário')
        extra_fields.setdefault('registration', '000000000')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superusuário precisa de is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superusuário precisa de is_superuser=True.')

        return self.create_user(email, password, **extra_fields)