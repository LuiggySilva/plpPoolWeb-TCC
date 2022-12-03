# Generated by Django 3.2.16 on 2022-12-03 16:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plpPool', '0004_delete_schedulerinfo'),
    ]

    operations = [
        migrations.CreateModel(
            name='BackupDB',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='backup/')),
            ],
        ),
        migrations.AlterField(
            model_name='periodo',
            name='monitores',
            field=models.ManyToManyField(related_name='monitores', to='plpPool.Monitor'),
        ),
    ]
