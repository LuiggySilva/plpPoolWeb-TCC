# Generated by Django 3.2.8 on 2022-06-27 15:30

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plpPool', '0006_alter_user_username'),
    ]

    operations = [
        migrations.AlterField(
            model_name='monitor',
            name='matricula',
            field=models.CharField(max_length=9, unique=True, validators=[django.core.validators.RegexValidator('^\\d{9}$', 'Formato de matrícula inválido')], verbose_name='Matrícula'),
        ),
    ]
