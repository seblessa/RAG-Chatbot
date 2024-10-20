# Generated by Django 5.1 on 2024-09-06 12:05

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chatapp', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='chatmessage',
            name='source',
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='response',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='session',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='chatapp.chatinstance'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='ruleset',
            name='default_set',
            field=models.BooleanField(default=False),
        ),
    ]