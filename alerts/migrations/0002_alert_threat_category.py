# Generated by Django 5.2.1 on 2025-05-21 17:04

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('alerts', '0001_initial'),
        ('cases', '0002_threatcategory_tasktemplate'),
    ]

    operations = [
        migrations.AddField(
            model_name='alert',
            name='threat_category',
            field=models.ForeignKey(blank=True, help_text='Type of threat for automated task generation', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='alerts', to='cases.threatcategory', verbose_name='Threat Category'),
        ),
    ]
