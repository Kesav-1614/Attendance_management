# Generated by Django 5.1.7 on 2025-03-18 06:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0030_remove_payroll_hourly_rate_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='attendance',
            name='break_in',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='attendance',
            name='break_out',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
