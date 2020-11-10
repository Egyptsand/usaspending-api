import asyncio
import logging

from django.db import connection
from django.core.management.base import BaseCommand

from usaspending_api.common.data_connectors.async_sql_query import async_run_update
from usaspending_api.common.helpers.timing_helpers import ConsoleTimer as Timer

logger = logging.getLogger("script")

UPDATE_AWARDS_SQL = """
WITH recent_covid_awards AS (
    SELECT
        DISTINCT ON
        (faba.award_id) faba.award_id, sa.submission_id, sa.is_final_balances_for_fy, sa.reporting_fiscal_year, sa.reporting_fiscal_period, sa.quarter_format_flag
    FROM
        financial_accounts_by_awards faba
    INNER JOIN disaster_emergency_fund_code defc ON
        defc.code = faba.disaster_emergency_fund_code
        AND defc.group_name = 'covid_19'
    INNER JOIN submission_attributes sa ON
        sa.reporting_period_start >= '2020-04-01'
        AND faba.submission_id = sa.submission_id
    INNER JOIN dabs_submission_window_schedule dabs ON
        dabs.id = sa.submission_window_id
        AND dabs.submission_reveal_date <= now()
    WHERE
        faba.award_id IS NOT NULL
    ORDER BY
        faba.award_id, submission_reveal_date DESC, is_quarter
),
last_periods_covid_awards AS (
    SELECT
        DISTINCT award_id
    FROM
        financial_accounts_by_awards faba
    INNER JOIN submission_attributes sa ON
        faba.submission_id = sa.submission_id
    INNER JOIN dabs_submission_window_schedule dabs ON
        dabs.id = sa.submission_window_id
    INNER JOIN disaster_emergency_fund_code defc ON
        defc.code = faba.disaster_emergency_fund_code
        AND defc.group_name = 'covid_19'
    WHERE
        (
            submission_fiscal_year = {last_months_year}
            AND submission_fiscal_month = {last_months_month}
            AND is_quarter = FALSE
        )
        OR (
            submission_fiscal_year = {last_quarters_year}
            AND submission_fiscal_month = {last_quarters_month}
            AND is_quarter = TRUE
        )
)
UPDATE
    awards
SET
    update_date = NOW()
WHERE
    id IN (
        SELECT
            *
        FROM
            last_periods_covid_awards
    )
    AND id IN (
        SELECT
            award_id
        FROM
            recent_covid_awards
        WHERE
            recent_covid_awards.is_final_balances_for_fy = FALSE
    )
    AND update_date < '{submission_reveal_date}'
"""

UPDATE_AWARDS_BROAD_SQL = """
WITH covid_awards AS (
    SELECT
        DISTINCT ON
        (faba.award_id) faba.award_id, sa.submission_id, sa.is_final_balances_for_fy, sa.reporting_fiscal_year, sa.reporting_fiscal_period, sa.quarter_format_flag
    FROM
        financial_accounts_by_awards faba
    INNER JOIN disaster_emergency_fund_code defc ON
        defc.code = faba.disaster_emergency_fund_code
        AND defc.group_name = 'covid_19'
    INNER JOIN submission_attributes sa ON
        sa.reporting_period_start >= '2020-04-01'
        AND faba.submission_id = sa.submission_id
    INNER JOIN dabs_submission_window_schedule dabs ON
        dabs.id = sa.submission_window_id
        AND dabs.submission_reveal_date <= now()
    WHERE
        faba.award_id IS NOT NULL
    ORDER BY
        faba.award_id, submission_reveal_date DESC, is_quarter
)
UPDATE
    awards
SET
    update_date = NOW()
WHERE
    id IN (
        SELECT
            award_id
        FROM
            covid_awards
        WHERE
            covid_awards.is_final_balances_for_fy = FALSE
    )
    AND update_date < '{}'
"""

RECENT_PERIOD_SQL = """
SELECT
    submission_fiscal_month,
    submission_fiscal_year,
    is_quarter,
    submission_reveal_date
FROM
    dabs_submission_window_schedule
WHERE
    is_quarter = {}
    AND submission_reveal_date < NOW()
ORDER BY
    submission_fiscal_year DESC,
    submission_fiscal_month DESC
LIMIT 2
"""


class Command(BaseCommand):

    help = (
        "This command sets the 'update_date' field on award records with Covid"
        "faba records present in a submission from the previous submission but"
        "not in the current period's submission."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--broad",
            action="store_true",
            default=False,
            help="If this option is selected, ALL covid awards not present in the current period will be updated",
        )

    def handle(self, *args, **options):
        recent_periods = self.retreive_recent_periods()

        if not options["broad"]:
            self.update_awards(recent_periods)
        else:
            logger.info("Broad flag provided. Updating all Covid awards not reported in the latest submission")
            self.update_awards_broad(recent_periods)

    def retreive_recent_periods(self):
        # Open connection to database
        with connection.cursor() as cursor:

            # Query for most recent closed month periods
            cursor.execute(RECENT_PERIOD_SQL.format("FALSE"))
            recent_month_periods = cursor.fetchmany(2)

            # Query for most recent closed quarter periods
            cursor.execute(RECENT_PERIOD_SQL.format("TRUE"))
            recent_quarter_periods = cursor.fetchmany(2)

        recent_periods = {
            "this_month": self.read_period_fields(recent_month_periods[0]),
            "last_month": self.read_period_fields(recent_month_periods[1]),
            "last_quarter": self.read_period_fields(recent_quarter_periods[1])
        }

        return recent_periods

    def read_period_fields(self, period):
        return {"month": period[0], "year": period[1], "submission_reveal_date": period[3]}

    def update_awards(self, periods):
        submission_reveal_date = periods["this_month"]["submission_reveal_date"]

        # Open connection to database
        with connection.cursor() as cursor:
            cursor.execute(UPDATE_AWARDS_SQL.format(                    
                last_months_year=periods["last_month"]["year"],
                last_months_month=periods["last_month"]["month"],
                last_quarters_year=periods["last_quarter"]["year"],
                last_quarters_month=periods["last_quarter"]["month"],
                submission_reveal_date=submission_reveal_date
            ))
            logger.info(f"Update message (records updated): {cursor.statusmessage}")

    def update_awards_broad(self, periods):
        submission_reveal_date = periods["this_month"]["submission_reveal_date"]

        # Open connection to database
        with connection.cursor() as cursor:
            cursor.execute(UPDATE_AWARDS_BROAD_SQL.format(submission_reveal_date))
            logger.info(f"Update message (records updated): {cursor.statusmessage}")
