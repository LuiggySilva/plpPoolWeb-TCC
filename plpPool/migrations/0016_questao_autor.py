# Generated by Django 3.2.8 on 2022-06-27 19:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('plpPool', '0015_auto_20220627_1617'),
    ]

    operations = [
        migrations.AddField(
            model_name='questao',
            name='autor',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.DO_NOTHING, to='plpPool.monitor'),
            preserve_default=False,
        ),
    ]
