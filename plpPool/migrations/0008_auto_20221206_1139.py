# Generated by Django 3.2.16 on 2022-12-06 14:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plpPool', '0007_alter_backupdb_file'),
    ]

    operations = [
        migrations.AlterField(
            model_name='teste',
            name='entrada',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='teste',
            name='saida',
            field=models.TextField(blank=True, verbose_name='Saída'),
        ),
    ]
