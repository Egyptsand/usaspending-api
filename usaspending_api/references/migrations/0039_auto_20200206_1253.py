# Generated by Django 2.2.9 on 2020-02-06 12:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('references', '0038_delete_location'),
    ]

    operations = [
        migrations.CreateModel(
            name='CityCountyStateCode',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('feature_id', models.IntegerField()),
                ('feature_name', models.TextField(blank=True, null=True)),
                ('feature_class', models.TextField(blank=True, null=True)),
                ('census_code', models.TextField(blank=True, null=True)),
                ('census_class_code', models.TextField(blank=True, null=True)),
                ('gsa_code', models.TextField(blank=True, null=True)),
                ('opm_code', models.TextField(blank=True, null=True)),
                ('state_numeric', models.TextField(blank=True, db_index=True, null=True)),
                ('state_alpha', models.TextField()),
                ('county_sequence', models.IntegerField(blank=True, null=True)),
                ('county_numeric', models.TextField(blank=True, null=True)),
                ('county_name', models.TextField(blank=True, null=True)),
                ('primary_latitude', models.DecimalField(decimal_places=8, max_digits=13)),
                ('primary_longitude', models.DecimalField(decimal_places=8, max_digits=13)),
                ('date_created', models.DateField(blank=True, null=True)),
                ('date_edited', models.DateField(blank=True, null=True)),
            ],
            options={
                'db_table': 'ref_city_county_state_code',
            },
        ),
        migrations.DeleteModel(
            name='RefCityCountyCode',
        ),

        # Special index used to guarantee uniquity on the natural key columns.
        migrations.RunSQL(
            sql=["""
                create unique index idx_ref_city_county_state_code_natural_key on ref_city_county_state_code (
                    feature_id,
                    state_alpha,
                    coalesce(county_sequence, -1),
                    coalesce(county_numeric, '')
                )
            """],
        ),
    ]
