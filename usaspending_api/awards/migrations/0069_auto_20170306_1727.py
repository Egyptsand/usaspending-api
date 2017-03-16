# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-03-06 17:27
from __future__ import unicode_literals

from django.db import migrations, models
from django.db.models import F
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('references', '0053_auto_20170210_1814'),
        ('awards', '0068_merge_20170216_1631'),
    ]

    operations = [
        migrations.AddField(
            model_name='transactionassistance',
            name='cfda',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='references.CFDAProgram'),
        ),
        migrations.AlterField(
            model_name='transactionassistance',
            name='transaction',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='assistance_data', serialize=False, to='awards.Transaction'),
        ),
        migrations.AlterField(
            model_name='transactioncontract',
            name='transaction',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='contract_data', serialize=False, to='awards.Transaction'),
        )
    ]
