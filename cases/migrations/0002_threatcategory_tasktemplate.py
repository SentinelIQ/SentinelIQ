# Generated by Django 5.2.1 on 2025-05-21 16:58

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '0001_initial'),
        ('organizations', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ThreatCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(choices=[('phishing', 'Phishing'), ('malware', 'Malware'), ('ransomware', 'Ransomware'), ('data_breach', 'Data Breach'), ('insider_threat', 'Insider Threat'), ('ddos', 'DDoS'), ('unauthorized_access', 'Unauthorized Access'), ('social_engineering', 'Social Engineering'), ('supply_chain', 'Supply Chain'), ('other', 'Other')], max_length=50, unique=True, verbose_name='Name')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('icon_class', models.CharField(blank=True, max_length=50, verbose_name='Icon Class')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
            ],
            options={
                'verbose_name': 'Threat Category',
                'verbose_name_plural': 'Threat Categories',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='TaskTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255, verbose_name='Title')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('priority', models.CharField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], default='medium', max_length=10, verbose_name='Priority')),
                ('is_active', models.BooleanField(default=True, verbose_name='Active')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Order')),
                ('due_days', models.PositiveIntegerField(default=7, help_text='Number of days after case creation to set as due date', verbose_name='Due Days')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='task_templates', to='organizations.organization')),
                ('threat_category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='task_templates', to='cases.threatcategory', verbose_name='Threat Category')),
            ],
            options={
                'verbose_name': 'Task Template',
                'verbose_name_plural': 'Task Templates',
                'ordering': ['threat_category', 'order', 'title'],
            },
        ),
    ]
