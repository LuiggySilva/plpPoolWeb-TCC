# Generated by Django 3.2.8 on 2022-06-27 22:04

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plpPool', '0019_alter_user_slug'),
    ]

    operations = [
        migrations.AlterField(
            model_name='linguagem',
            name='extensao',
            field=models.CharField(max_length=50, validators=[django.core.validators.RegexValidator('^.\\w*$', 'Formato de extensão inválido')], verbose_name='Extensão'),
        ),
    ]
