# Generated by Django 3.2.7 on 2025-03-11 08:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0022_auto_20250307_1251'),
    ]

    operations = [
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
            ],
        ),
    ]
