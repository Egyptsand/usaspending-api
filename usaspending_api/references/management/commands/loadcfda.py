import logging
import pandas as pd

from datetime import datetime, timezone
from time import perf_counter

from django.core.management.base import BaseCommand

from usaspending_api.common.url_helpers import RetrieveFileFromUri, DISPLAY_ALL_SCHEMAS
from usaspending_api.references.models import Cfda


logger = logging.getLogger("console")

DATA_CLEANING_MAP = {
    "program_title": "program_title",
    "program_number": "program_number",
    "popular_name_(020)": "popular_name",
    "federal_agency_(030)": "federal_agency",
    "authorization_(040)": "authorization",
    "objectives_(050)": "objectives",
    "types_of_assistance_(060)": "types_of_assistance",
    "uses_and_use_restrictions_(070)": "uses_and_use_restrictions",
    "applicant_eligibility_(081)": "applicant_eligibility",
    "beneficiary_eligibility_(082)": "beneficiary_eligibility",
    "credentials/documentation_(083)": "credentials_documentation",
    "preapplication_coordination_(091)": "pre_application_coordination",
    "application_procedures_(092)": "application_procedures",
    "award_procedure_(093)": "award_procedure",
    "deadlines_(094)": "deadlines",
    "range_of_approval/disapproval_time_(095)": "range_of_approval_disapproval_time",
    "appeals_(096)": "appeals",
    "renewals_(097)": "renewals",
    "formula_and_matching_requirements_(101)": "formula_and_matching_requirements",
    "length_and_time_phasing_of_assistance_(102)": "length_and_time_phasing_of_assistance",
    "reports_(111)": "reports",
    "audits_(112)": "audits",
    "records_(113)": "records",
    "account_identification_(121)": "account_identification",
    "obligations_(122)": "obligations",
    "range_and_average_of_financial_assistance_(123)": "range_and_average_of_financial_assistance",
    "program_accomplishments_(130)": "program_accomplishments",
    "regulations__guidelines__and_literature_(140)": "regulations_guidelines_and_literature",
    "regional_or__local_office_(151)": "regional_or_local_office",
    "headquarters_office_(152)": "headquarters_office",
    "website_address_(153)": "website_address",
    "related_programs_(160)": "related_programs",
    "examples_of_funded_projects_(170)": "examples_of_funded_projects",
    "criteria_for_selecting_proposals_(180)": "criteria_for_selecting_proposals",
    "url": "url",
    "recovery": "recovery",
    "omb_agency_code": "omb_agency_code",
    "omb_bureau_code": "omb_bureau_code",
    "published_date": "published_date",
    "archived_date": "archived_date",
}


class Command(BaseCommand):

    help = "Load new CFDA data into references_cfda from the provided source CSV file"

    def add_arguments(self, parser):
        arg_help = "Provide a valid RFC URL for a CFDA file: {}"
        parser.add_argument("cfda-data-url", type=str, help=arg_help.format(DISPLAY_ALL_SCHEMAS))

    def handle(self, *args, **options):
        logger.info("Starting Script. Loading data into pandas DataFrames")
        start_time = datetime.now(timezone.utc).isoformat()
        start = perf_counter()
        external_data_df = load_from_url(options["cfda-data-url"])
        database_df = load_cfda_table_into_pandas()

        logger.info("Remodel DataFrames for comparision")
        external_data_df = fully_order_pandas_dataframe(external_data_df, "program_number")
        database_df = fully_order_pandas_dataframe(database_df, "program_number")

        logger.info("Compare DataFrames")
        raise_status_code_3 = not load_cfda(database_df, external_data_df)

        logger.info("Script started at {} and took {:.4f}s".format(start_time, perf_counter() - start))

        if raise_status_code_3:
            raise SystemExit(3)


def load_from_url(rfc_path_string):
    with RetrieveFileFromUri(rfc_path_string).get_file_object() as data_file_handle:
        return load_cfda_csv_into_pandas(data_file_handle)


def load_cfda_csv_into_pandas(data_file_handle):
    df = pd.read_csv(data_file_handle, dtype=str, encoding="latin1", na_filter=False)
    df.rename(columns=clean_col_names, inplace=True)

    for field in DATA_CLEANING_MAP.keys():
        if field not in list(df.columns):
            raise ValueError("{} is required for loading table".format(field))

    df = df[list(DATA_CLEANING_MAP.keys())]  # toss out any columns from the csv that aren't in the fieldMap parameter
    df = df.rename(columns=DATA_CLEANING_MAP)  # rename columns as specified in fieldMap
    df["data_source"] = "USA"
    return df


def clean_col_names(field):
    """Define some data-munging functions that can be applied to pandas
    dataframes as necessary"""
    return str(field).lower().strip().replace(" ", "_").replace(",", "_")


def load_cfda_table_into_pandas():
    database_records = list(Cfda.objects.all().values())
    df = pd.DataFrame(database_records, dtype=str)
    del df["id"]
    del df["create_date"]
    del df["update_date"]
    return df


def fully_order_pandas_dataframe(df, sort_column):
    df.sort_values(sort_column, inplace=True)  # sort the values using the provided column
    df = df[sorted(df.columns.tolist())]  # order the dataframe columns
    df.reset_index(drop=True, inplace=True)  # reset the indexes to match the new order
    return df


def load_cfda(original_df, new_df):
    if new_df.equals(original_df):
        logger.info("Skipping CFDA load, no new data.")
        return False

    new_record_count, updated_record_count = 0, 0

    logger.info("Inserting new CFDA data.")
    for row in new_df.itertuples():
        record = row._asdict()
        del record["Index"]
        _, created = Cfda.objects.update_or_create(program_number=record["program_number"], defaults=record)
        if created:
            new_record_count += 1
        else:
            updated_record_count += 1
    logger.info("Completed loading new data. New: {}, Updated: {}".format(new_record_count, updated_record_count))
    return True
