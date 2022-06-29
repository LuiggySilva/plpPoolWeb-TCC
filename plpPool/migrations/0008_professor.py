# Generated by Django 3.2.8 on 2022-06-27 15:40

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('plpPool', '0007_alter_monitor_matricula'),
    ]

    operations = [
        migrations.CreateModel(
            name='Professor',
            fields=[
                ('user_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='plpPool.user')),
            ],
            options={
                'verbose_name': 'Professor',
                'verbose_name_plural': 'Professores',
            },
            bases=('plpPool.user',),
        ),
    ]
