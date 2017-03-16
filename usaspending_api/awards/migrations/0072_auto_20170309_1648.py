# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-03-09 16:48
from __future__ import unicode_literals

from django.db import migrations
from usaspending_api.etl.award_helpers import *


def update_potential_values(apps, schema_editor):
    # Use award model at time of migration
    Award = apps.get_model("awards", "Award")
    # Update all awards
    update_awards()
    update_contract_awards(tuple(Award.objects.filter(transaction__contract_data__isnull=False).values_list('id', flat=True)))


class Migration(migrations.Migration):

    dependencies = [
        ('awards', '0071_merge_20170308_1607'),
    ]

    operations = [
        migrations.RunPython(update_potential_values),
    ]
