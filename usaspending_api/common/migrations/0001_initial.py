# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-05-03 15:46
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='RequestCatalog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request', django.contrib.postgres.fields.jsonb.JSONField(help_text='The serialized form of the POST request')),
                ('checksum', models.CharField(db_index=True, help_text='The SHA-256 checksum of the serialized POST request', max_length=256, unique=True)),
                ('create_date', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_accessed', models.DateTimeField(auto_now_add=True, null=True)),
            ],
            options={
                'managed': True,
                'db_table': 'request_catalog',
            },
        ),
    ]
