# Generated by Django 3.2.8 on 2022-06-28 00:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('plpPool', '0024_deadline'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='linguagem',
            options={'verbose_name': 'Linguagem', 'verbose_name_plural': 'Linguagens'},
        ),
        migrations.AddField(
            model_name='deadline',
            name='periodo',
            field=models.ForeignKey(blank=True, default=1, on_delete=django.db.models.deletion.CASCADE, to='plpPool.periodo'),
            preserve_default=False,
        ),
    ]
