import logging
import time

from copy import copy
from datetime import datetime, timezone
from django.db import connection, transaction

from usaspending_api.awards.models import TransactionFABS, TransactionNormalized, Award
from usaspending_api.broker.helpers.get_business_categories import get_business_categories
from usaspending_api.common.helpers.date_helper import cast_datetime_to_utc
from usaspending_api.common.helpers.dict_helpers import upper_case_dict_values
from usaspending_api.common.helpers.etl_helpers import update_c_to_d_linkages
from usaspending_api.common.helpers.date_helper import fy
from usaspending_api.common.helpers.timing_helpers import timer
from usaspending_api.etl.award_helpers import prune_empty_awards, update_awards, update_assistance_awards
from usaspending_api.etl.broker_etl_helpers import dictfetchall
from usaspending_api.etl.management.load_base import load_data_into_model, format_date
from usaspending_api.references.models import Agency


logger = logging.getLogger("script")

BATCH_FETCH_SIZE = 25000


def fetch_fabs_data_generator(dap_uid_list):
    db_cursor = connection.cursor()
    db_query = """
        SELECT * FROM source_assistance_transaction
        WHERE published_fabs_id IN %s;
    """

    total_uid_count = len(dap_uid_list)

    for i in range(0, total_uid_count, BATCH_FETCH_SIZE):
        start_time = time.perf_counter()
        max_index = i + BATCH_FETCH_SIZE if i + BATCH_FETCH_SIZE < total_uid_count else total_uid_count
        fabs_ids_batch = dap_uid_list[i:max_index]

        logger.info(f"Fetching {i + 1}-{max_index} out of {total_uid_count} records from source table")
        db_cursor.execute(db_query, [tuple(fabs_ids_batch)])
        logger.info("Fetching records took {:.2f}s".format(time.perf_counter() - start_time))

        yield dictfetchall(db_cursor)


@transaction.atomic
def insert_all_new_fabs(all_new_to_insert):
    update_award_ids = []
    for to_insert in fetch_fabs_data_generator(all_new_to_insert):
        start = time.perf_counter()
        update_award_ids.extend(insert_new_fabs(to_insert))
        logger.info("FABS insertions took {:.2f}s".format(time.perf_counter() - start))
    return update_award_ids


def insert_new_fabs(to_insert):
    fabs_normalized_field_map = {
        "type": "assistance_type",
        "description": "award_description",
        "funding_amount": "total_funding_amount",
    }

    fabs_field_map = {
        "officer_1_name": "high_comp_officer1_full_na",
        "officer_1_amount": "high_comp_officer1_amount",
        "officer_2_name": "high_comp_officer2_full_na",
        "officer_2_amount": "high_comp_officer2_amount",
        "officer_3_name": "high_comp_officer3_full_na",
        "officer_3_amount": "high_comp_officer3_amount",
        "officer_4_name": "high_comp_officer4_full_na",
        "officer_4_amount": "high_comp_officer4_amount",
        "officer_5_name": "high_comp_officer5_full_na",
        "officer_5_amount": "high_comp_officer5_amount",
    }

    update_award_ids = []
    for row in to_insert:
        upper_case_dict_values(row)

        # Find the toptier awards from the subtier awards
        awarding_agency = Agency.get_by_subtier_only(row["awarding_sub_tier_agency_c"])
        funding_agency = Agency.get_by_subtier_only(row["funding_sub_tier_agency_co"])

        # Create the summary Award
        (created, award) = Award.get_or_create_summary_award(
            generated_unique_award_id=row["unique_award_key"],
            fain=row["fain"],
            uri=row["uri"],
            record_type=row["record_type"],
        )
        award.save()

        # Append row to list of Awards updated
        update_award_ids.append(award.id)

        try:
            last_mod_date = datetime.strptime(str(row["modified_at"]), "%Y-%m-%d %H:%M:%S.%f").date()
        except ValueError:
            last_mod_date = datetime.strptime(str(row["modified_at"]), "%Y-%m-%d %H:%M:%S").date()

        parent_txn_value_map = {
            "award": award,
            "awarding_agency": awarding_agency,
            "funding_agency": funding_agency,
            "period_of_performance_start_date": format_date(row["period_of_performance_star"]),
            "period_of_performance_current_end_date": format_date(row["period_of_performance_curr"]),
            "action_date": format_date(row["action_date"]),
            "last_modified_date": last_mod_date,
            "type_description": row["assistance_type_desc"],
            "transaction_unique_id": row["afa_generated_unique"],
            "business_categories": get_business_categories(row=row, data_type="fabs"),
        }

        transaction_normalized_dict = load_data_into_model(
            TransactionNormalized(),  # thrown away
            row,
            field_map=fabs_normalized_field_map,
            value_map=parent_txn_value_map,
            as_dict=True,
        )

        financial_assistance_data = load_data_into_model(
            TransactionFABS(), row, field_map=fabs_field_map, as_dict=True  # thrown away
        )

        # Hack to cut back on the number of warnings dumped to the log.
        financial_assistance_data["updated_at"] = cast_datetime_to_utc(financial_assistance_data["updated_at"])
        financial_assistance_data["created_at"] = cast_datetime_to_utc(financial_assistance_data["created_at"])
        financial_assistance_data["modified_at"] = cast_datetime_to_utc(financial_assistance_data["modified_at"])

        afa_generated_unique = financial_assistance_data["afa_generated_unique"]
        unique_fabs = TransactionFABS.objects.filter(afa_generated_unique=afa_generated_unique)

        if unique_fabs.first():
            transaction_normalized_dict["update_date"] = datetime.now(timezone.utc)
            transaction_normalized_dict["fiscal_year"] = fy(transaction_normalized_dict["action_date"])

            # Update TransactionNormalized
            TransactionNormalized.objects.filter(id=unique_fabs.first().transaction.id).update(
                **transaction_normalized_dict
            )

            # Update TransactionFABS
            unique_fabs.update(**financial_assistance_data)
        else:
            # Create TransactionNormalized
            transaction_normalized = TransactionNormalized(**transaction_normalized_dict)
            transaction_normalized.save()

            # Create TransactionFABS
            transaction_fabs = TransactionFABS(transaction=transaction_normalized, **financial_assistance_data)
            transaction_fabs.save()

    return update_award_ids


def upsert_fabs_transactions(ids_to_upsert, update_and_delete_award_ids):
    if ids_to_upsert or update_and_delete_award_ids:
        update_award_ids = copy(update_and_delete_award_ids)

        if ids_to_upsert:
            with timer("inserting new FABS data", logger.info):
                update_award_ids.extend(insert_all_new_fabs(ids_to_upsert))

        if update_award_ids:
            update_award_ids = tuple(set(update_award_ids))  # Convert to tuple and remove duplicates.
            with timer("updating awards to reflect their latest associated transaction info", logger.info):
                award_record_count = update_awards(update_award_ids)
                logger.info(f"{award_record_count} awards updated from their transactional data")
            with timer("deleting awards that no longer have a transaction", logger.info):
                award_record_count = prune_empty_awards(update_award_ids)
                logger.info(f"{award_record_count} awards deleted")
            with timer("updating awards with executive compensation data", logger.info):
                award_record_count = update_assistance_awards(update_award_ids)
                logger.info(f"{award_record_count} awards updated FABS-specific and exec comp data")

        with timer("updating C->D linkages", logger.info):
            update_c_to_d_linkages("assistance")

    else:
        logger.info("Nothing to insert...")
