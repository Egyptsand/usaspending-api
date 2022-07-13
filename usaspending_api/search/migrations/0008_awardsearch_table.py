# Generated by Django 3.2.13 on 2022-07-13 18:03

import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.expressions


class Migration(migrations.Migration):

    dependencies = [
        ('awards', '0095_auto_20220617_1620'),
        ('search', '0007_transactionsearch_parent_uei'),
    ]

    operations = [
        migrations.CreateModel(
            name='AwardSearch',
            fields=[
                ('treasury_account_identifiers', django.contrib.postgres.fields.ArrayField(base_field=models.IntegerField(), default=None, size=None)),
                ('award', models.OneToOneField(on_delete=django.db.models.deletion.DO_NOTHING, primary_key=True, related_name='awardsearch', serialize=False, to='awards.award')),
                ('category', models.TextField()),
                ('type', models.TextField()),
                ('type_description', models.TextField()),
                ('generated_unique_award_id', models.TextField()),
                ('display_award_id', models.TextField()),
                ('update_date', models.DateField()),
                ('piid', models.TextField()),
                ('fain', models.TextField()),
                ('uri', models.TextField()),
                ('award_amount', models.DecimalField(decimal_places=2, max_digits=23)),
                ('total_obligation', models.DecimalField(decimal_places=2, max_digits=23)),
                ('description', models.TextField()),
                ('total_subsidy_cost', models.DecimalField(decimal_places=2, max_digits=23)),
                ('total_loan_value', models.DecimalField(decimal_places=2, max_digits=23)),
                ('total_obl_bin', models.TextField()),
                ('recipient_hash', models.UUIDField()),
                ('recipient_levels', django.contrib.postgres.fields.ArrayField(base_field=models.TextField(), default=list, size=None)),
                ('recipient_name', models.TextField()),
                ('recipient_unique_id', models.TextField()),
                ('parent_recipient_unique_id', models.TextField()),
                ('business_categories', django.contrib.postgres.fields.ArrayField(base_field=models.TextField(), default=list, size=None)),
                ('action_date', models.DateField()),
                ('fiscal_year', models.IntegerField()),
                ('last_modified_date', models.TextField()),
                ('period_of_performance_start_date', models.DateField()),
                ('period_of_performance_current_end_date', models.DateField()),
                ('date_signed', models.DateField()),
                ('ordering_period_end_date', models.DateField(null=True)),
                ('original_loan_subsidy_cost', models.DecimalField(decimal_places=2, max_digits=23)),
                ('face_value_loan_guarantee', models.DecimalField(decimal_places=2, max_digits=23)),
                ('awarding_agency_id', models.IntegerField()),
                ('funding_agency_id', models.IntegerField()),
                ('funding_toptier_agency_id', models.IntegerField()),
                ('funding_subtier_agency_id', models.IntegerField()),
                ('awarding_toptier_agency_name', models.TextField()),
                ('funding_toptier_agency_name', models.TextField()),
                ('awarding_subtier_agency_name', models.TextField()),
                ('funding_subtier_agency_name', models.TextField()),
                ('awarding_toptier_agency_code', models.TextField()),
                ('funding_toptier_agency_code', models.TextField()),
                ('awarding_subtier_agency_code', models.TextField()),
                ('funding_subtier_agency_code', models.TextField()),
                ('recipient_location_country_code', models.TextField()),
                ('recipient_location_country_name', models.TextField()),
                ('recipient_location_state_code', models.TextField()),
                ('recipient_location_county_code', models.TextField()),
                ('recipient_location_county_name', models.TextField()),
                ('recipient_location_zip5', models.TextField()),
                ('recipient_location_congressional_code', models.TextField()),
                ('recipient_location_city_name', models.TextField()),
                ('recipient_location_state_name', models.TextField()),
                ('recipient_location_state_fips', models.TextField()),
                ('recipient_location_state_population', models.IntegerField()),
                ('recipient_location_county_population', models.IntegerField()),
                ('recipient_location_congressional_population', models.IntegerField()),
                ('pop_country_code', models.TextField()),
                ('pop_country_name', models.TextField()),
                ('pop_state_code', models.TextField()),
                ('pop_county_code', models.TextField()),
                ('pop_county_name', models.TextField()),
                ('pop_city_code', models.TextField()),
                ('pop_zip5', models.TextField()),
                ('pop_congressional_code', models.TextField()),
                ('pop_city_name', models.TextField()),
                ('pop_state_name', models.TextField()),
                ('pop_state_fips', models.TextField()),
                ('pop_state_population', models.IntegerField()),
                ('pop_county_population', models.IntegerField()),
                ('pop_congressional_population', models.IntegerField()),
                ('cfda_program_title', models.TextField()),
                ('cfda_number', models.TextField()),
                ('sai_number', models.TextField()),
                ('type_of_contract_pricing', models.TextField()),
                ('extent_competed', models.TextField()),
                ('type_set_aside', models.TextField()),
                ('product_or_service_code', models.TextField()),
                ('product_or_service_description', models.TextField()),
                ('naics_code', models.TextField()),
                ('naics_description', models.TextField()),
                ('tas_paths', django.contrib.postgres.fields.ArrayField(base_field=models.TextField(), default=list, size=None)),
                ('tas_components', django.contrib.postgres.fields.ArrayField(base_field=models.TextField(), default=list, size=None)),
                ('disaster_emergency_fund_codes', django.contrib.postgres.fields.ArrayField(base_field=models.TextField(), default=list, size=None)),
                ('covid_spending_by_defc', models.JSONField()),
                ('total_covid_outlay', models.DecimalField(decimal_places=2, max_digits=23)),
                ('total_covid_obligation', models.DecimalField(decimal_places=2, max_digits=23)),
            ],
            options={
                'db_table': 'rpt"."award_search',
            },
        ),
        migrations.AddIndex(
            model_name='awardsearch',
            index=models.Index(fields=['award_id'], name='as_idx_award_id'),
        ),
        migrations.AddIndex(
            model_name='awardsearch',
            index=models.Index(condition=models.Q(('action_date__gte', '2007-10-01')), fields=['recipient_hash'], name='as_idx_recipient_hash'),
        ),
        migrations.AddIndex(
            model_name='awardsearch',
            index=models.Index(condition=models.Q(('recipient_unique_id__isnull', False), ('action_date__gte', '2007-10-01')), fields=['recipient_unique_id'], name='as_idx_recipient_unique_id'),
        ),
        migrations.AddIndex(
            model_name='awardsearch',
            index=models.Index(django.db.models.expressions.OrderBy(django.db.models.expressions.F('action_date'), descending=True, nulls_last=True), condition=models.Q(('action_date__gte', '2007-10-01')), name='as_idx_action_date'),
        ),
        migrations.AddIndex(
            model_name='awardsearch',
            index=models.Index(condition=models.Q(('action_date__gte', '2007-10-01')), fields=['funding_agency_id'], name='as_idx_funding_agency_id'),
        ),
        migrations.AddIndex(
            model_name='awardsearch',
            index=models.Index(condition=models.Q(('action_date__gte', '2007-10-01')), fields=['recipient_location_congressional_code'], name='as_idx_recipient_cong_code'),
        ),
        migrations.AddIndex(
            model_name='awardsearch',
            index=models.Index(condition=models.Q(('action_date__gte', '2007-10-01')), fields=['recipient_location_county_code'], name='as_idx_recipient_county_code'),
        ),
        migrations.AddIndex(
            model_name='awardsearch',
            index=models.Index(condition=models.Q(('action_date__gte', '2007-10-01')), fields=['recipient_location_state_code'], name='as_idx_recipient_state_code'),
        ),
        migrations.AddIndex(
            model_name='awardsearch',
            index=models.Index(django.db.models.expressions.OrderBy(django.db.models.expressions.F('action_date'), descending=True, nulls_last=True), condition=models.Q(('action_date__lt', '2007-10-01')), name='as_idx_action_date_pre2008'),
        ),
        migrations.DeleteModel(
            name='AwardSearchView',
        ),
        migrations.DeleteModel(
            name='ContractAwardSearchMatview',
        ),
        migrations.DeleteModel(
            name='DirectPaymentAwardSearchMatview',
        ),
        migrations.DeleteModel(
            name='GrantAwardSearchMatview',
        ),
        migrations.DeleteModel(
            name='IDVAwardSearchMatview',
        ),
        migrations.DeleteModel(
            name='LoanAwardSearchMatview',
        ),
        migrations.DeleteModel(
            name='OtherAwardSearchMatview',
        ),
        migrations.DeleteModel(
            name='Pre2008AwardSearchMatview',
        ),
    ]
