# Generated by Django 5.2.1 on 2025-05-21 16:37

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('alerts', '0001_initial'),
        ('core', '0001_initial'),
        ('organizations', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Case',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255, verbose_name='Title')),
                ('description', models.TextField(verbose_name='Description')),
                ('priority', models.CharField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')], default='medium', max_length=10, verbose_name='Priority')),
                ('status', models.CharField(choices=[('open', 'Open'), ('in_progress', 'In Progress'), ('pending', 'Pending'), ('resolved', 'Resolved'), ('closed', 'Closed')], default='open', max_length=15, verbose_name='Status')),
                ('due_date', models.DateField(blank=True, null=True, verbose_name='Due Date')),
                ('tlp', models.CharField(choices=[('white', 'TLP:WHITE'), ('green', 'TLP:GREEN'), ('amber', 'TLP:AMBER'), ('red', 'TLP:RED')], default='amber', help_text='Traffic Light Protocol - Confidentiality of information', max_length=10, verbose_name='TLP')),
                ('pap', models.CharField(choices=[('white', 'PAP:WHITE'), ('green', 'PAP:GREEN'), ('amber', 'PAP:AMBER'), ('red', 'PAP:RED')], default='amber', help_text='Permissible Actions Protocol - Level of exposure of information', max_length=10, verbose_name='PAP')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('assigned_to', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_cases', to=settings.AUTH_USER_MODEL)),
                ('mitre_attack_groups', models.ManyToManyField(blank=True, help_text='Grupos de elementos MITRE ATT&CK (táticas, técnicas, subtécnicas) relacionados', related_name='cases', to='core.mitreattackgroup', verbose_name='MITRE ATT&CK Groups')),
                ('mitre_subtechniques', models.ManyToManyField(blank=True, related_name='cases', to='core.mitresubtechnique', verbose_name='MITRE Sub-techniques')),
                ('mitre_tactics', models.ManyToManyField(blank=True, related_name='cases', to='core.mitretactic', verbose_name='MITRE Tactics')),
                ('mitre_techniques', models.ManyToManyField(blank=True, related_name='cases', to='core.mitretechnique', verbose_name='MITRE Techniques')),
                ('observables', models.ManyToManyField(blank=True, related_name='cases', to='core.observable', verbose_name='Observables')),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cases', to='organizations.organization')),
                ('related_alerts', models.ManyToManyField(blank=True, related_name='related_cases', to='alerts.alert')),
                ('tags', models.ManyToManyField(blank=True, related_name='cases', to='core.tag', verbose_name='Tags')),
            ],
            options={
                'verbose_name': 'Case',
                'verbose_name_plural': 'Cases',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CaseAttachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='case_attachments/', verbose_name='File')),
                ('filename', models.CharField(max_length=255, verbose_name='Filename')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True, verbose_name='Uploaded at')),
                ('case', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='cases.case')),
                ('uploaded_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='case_attachments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Case Attachment',
                'verbose_name_plural': 'Case Attachments',
                'ordering': ['-uploaded_at'],
            },
        ),
        migrations.CreateModel(
            name='CaseComment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField(verbose_name='Content')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('case', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='cases.case')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='case_comments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Case Comment',
                'verbose_name_plural': 'Case Comments',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CaseEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_type', models.CharField(choices=[('created', 'Case Created'), ('status_changed', 'Status Changed'), ('priority_changed', 'Priority Changed'), ('assignee_changed', 'Assignee Changed'), ('due_date_changed', 'Due Date Changed'), ('comment_added', 'Comment Added'), ('attachment_added', 'Attachment Added'), ('alert_linked', 'Alert Linked'), ('alert_unlinked', 'Alert Unlinked'), ('tlp_changed', 'TLP Changed'), ('pap_changed', 'PAP Changed'), ('tags_changed', 'Tags Changed'), ('observable_added', 'Observable Added'), ('observable_removed', 'Observable Removed'), ('task_added', 'Task Added'), ('task_updated', 'Task Updated'), ('task_completed', 'Task Completed'), ('mitre_attack_added', 'MITRE ATT&CK Added'), ('mitre_attack_removed', 'MITRE ATT&CK Removed'), ('custom', 'Custom Event')], max_length=25, verbose_name='Event Type')),
                ('title', models.CharField(max_length=255, verbose_name='Event Title')),
                ('description', models.TextField(blank=True, verbose_name='Event Description')),
                ('old_value', models.CharField(blank=True, max_length=255, null=True, verbose_name='Old Value')),
                ('new_value', models.CharField(blank=True, max_length=255, null=True, verbose_name='New Value')),
                ('metadata', models.JSONField(blank=True, null=True, verbose_name='Metadata')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('case', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='timeline_events', to='cases.case')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='case_events', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Case Event',
                'verbose_name_plural': 'Case Events',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255, verbose_name='Title')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('due_date', models.DateField(blank=True, null=True, verbose_name='Due Date')),
                ('priority', models.CharField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], default='medium', max_length=10, verbose_name='Priority')),
                ('is_completed', models.BooleanField(default=False, verbose_name='Completed')),
                ('completed_at', models.DateTimeField(blank=True, null=True, verbose_name='Completed at')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('assigned_to', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_tasks', to=settings.AUTH_USER_MODEL)),
                ('case', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tasks', to='cases.case')),
                ('completed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='completed_tasks', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Task',
                'verbose_name_plural': 'Tasks',
                'ordering': ['is_completed', 'priority', 'due_date', '-created_at'],
            },
        ),
    ]
