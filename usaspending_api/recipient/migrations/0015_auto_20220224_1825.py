# Generated by Django 2.2.17 on 2022-02-24 18:25

from django.db import migrations
import partial_index


class Migration(migrations.Migration):

    dependencies = [
        ('recipient', '0014_auto_20220224_1536'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='recipientlookup',
            name='recipient_l_duns_bb057a_partial',
        ),
        migrations.AddIndex(
            model_name='recipientlookup',
            index=partial_index.PartialIndex(fields=['duns'], name='recipient_l_duns_a43c07_partial', unique=False, where=partial_index.PQ(duns__isnull=False)),
        ),
    ]
