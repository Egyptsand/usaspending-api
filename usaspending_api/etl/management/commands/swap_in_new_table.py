import logging
import re

from django.core.management import BaseCommand
from django.db import connection, transaction

from usaspending_api.common.helpers.sql_helpers import ordered_dictionary_fetcher

logger = logging.getLogger("script")


class Command(BaseCommand):
    help = """
    This command is used to swap two tables; the current and a new table with "_temp" appended.
    Validation is run against the new table to ensure that after the swap is complete all of the indexes, constraints,
    columns, and table name will be the same.

    NOTE: This entire process IS NOT ATOMIC (only the final swap of tables)!
    This choice was made to prevent potential deadlock scenarios since the swapping / renaming of indexes, constraints,
    and tables should only take milliseconds. If this command fails then any cleanup will have to be done manually.

    Current API and Download functionality is not affected until the step that actually renames the old table. That
    change will take an ACCESS EXCLUSIVE LOCK and any future queries following it will hit the new table. On a Primary
    database where typical query performance is under 1 minute this could cause some queries to take longer as they wait
    on the LOCK to be released, depending on what the lock is waiting on. For a Replica database this will cause some
    queries to cancel if they are blocking the ACCESS EXCLUSIVE LOCK for too long and could impede replication.

    At the time of the actual DROP TABLE command there should be no activity present on the old table since the
    ALTER TABLE for the rename would have blocked all activity and routed to the new table following the rename.
    """

    # Values are set in the beginning of "handle()"
    db_table_name: str
    temp_db_table_name: str

    # Query values are populated as they are run during validation and saved for re-use
    query_result_lookup = {
        "temp_table_constraints": [],
        "curr_table_constraints": [],
        "temp_table_indexes": [],
        "curr_table_indexes": [],
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--table",
            type=str,
            help="The active Postgres Table to swap with another containing the same name with '_temp' appended",
        )
        parser.add_argument(
            "--keep-old-data",
            action="store_true",
            default=False,
            help="Indicates whether or not to drop old table at the end of the command",
        )
        parser.add_argument(
            "--allow-foreign-key",
            action="store_true",
            default=False,
            help="A guard is enabled / disabled depending on the value of this flag. When 'FALSE' Foreign Keys are not"
            " allowed and both the active and new table are searched for any Foreign Keys before proceeding."
            " It is advised to not allow Foreign Key constraints since they can cause deadlock.",
        )

    def handle(self, *args, **options):
        self.db_table_name = options["table"]
        self.temp_db_table_name = f"{self.db_table_name}_temp"

        with connection.cursor() as cursor:
            self.validate_state_of_tables(cursor, options)
            self.swap_index_sql(cursor)
            self.swap_constraints_sql(cursor)
            self.swap_table_sql(cursor)
            if not options["keep_old_data"]:
                self.drop_old_table_sql(cursor)
            self.extra_sql(cursor)

    def swap_index_sql(self, cursor):
        logging.info("Renaming indexes of the new and old tables.")
        temp_indexes = self.query_result_lookup["temp_table_indexes"]
        curr_indexes = self.query_result_lookup["curr_table_indexes"]
        rename_sql = []
        sql_template = "ALTER INDEX {old_index_name} RENAME TO {new_index_name};"
        for val in curr_indexes:
            old_name = val["indexname"]
            new_name = f"{old_name}_old"
            rename_sql.append(sql_template.format(old_index_name=old_name, new_index_name=new_name))
        for val in temp_indexes:
            old_name = val["indexname"]
            new_name = re.match("^(.*)_temp$", old_name, flags=re.I)[1]
            rename_sql.append(sql_template.format(old_index_name=old_name, new_index_name=new_name))

        if rename_sql:
            cursor.execute("\n".join(rename_sql))

    def swap_constraints_sql(self, cursor):
        logging.info("Renaming constraints of the new and old tables.")
        temp_constraints = self.query_result_lookup["temp_table_constraints"]
        curr_constraints = self.query_result_lookup["curr_table_constraints"]
        rename_sql = []
        sql_template = "ALTER TABLE {table_name} RENAME CONSTRAINT {old_constraint_name} TO {new_constraint_name};"
        for val in curr_constraints:
            old_name = val["constraint_name"]
            new_name = f"{old_name}_old"
            rename_sql.append(
                sql_template.format(
                    table_name=self.db_table_name, old_constraint_name=old_name, new_constraint_name=new_name
                )
            )
        for val in temp_constraints:
            old_name = val["constraint_name"]
            new_name = re.match("^(.*)_temp$", old_name, flags=re.I)[1]
            rename_sql.append(
                sql_template.format(
                    table_name=self.temp_db_table_name, old_constraint_name=old_name, new_constraint_name=new_name
                )
            )

        if rename_sql:
            cursor.execute("\n".join(rename_sql))

    @transaction.atomic
    def swap_table_sql(self, cursor):
        logging.info("Renaming the new and old tables")
        sql_template = "ALTER TABLE {old_table_name} RENAME TO {new_table_name};"
        rename_sql = [
            sql_template.format(old_table_name=self.db_table_name, new_table_name=f"{self.db_table_name}_old"),
            sql_template.format(old_table_name=self.temp_db_table_name, new_table_name=f"{self.db_table_name}"),
        ]
        cursor.execute("\n".join(rename_sql))

    def drop_old_table_sql(self, cursor):
        # Instead of using CASCADE, all old constraints and indexes are dropped manually
        logging.info("Dropping the old table.")
        drop_sql = []
        indexes = self.query_result_lookup["curr_table_indexes"]
        constraints = self.query_result_lookup["curr_table_constraints"]
        for val in indexes:
            name = f"{val['indexname']}_old"
            drop_sql.append(f"DROP INDEX {name};")
        for val in constraints:
            name = f"{val['constraint_name']}_old"
            drop_sql.append(f"ALTER TABLE {self.db_table_name}_old DROP CONSTRAINT {name};")
        drop_sql.append(f"DROP TABLE {self.db_table_name}_old;")
        cursor.execute("\n".join(drop_sql))

    def extra_sql(self, cursor):
        cursor.execute(f"ANALYZE VERBOSE {self.db_table_name}")
        cursor.execute(f"GRANT SELECT ON {self.db_table_name} TO readonly")

    def validate_tables(self, cursor):
        logger.info("Verifying that the old table exists.")
        cursor.execute(f"SELECT * FROM information_schema.tables WHERE table_name = '{self.db_table_name}'")
        temp_tables = cursor.fetchall()
        if len(temp_tables) == 0:
            raise ValueError(f"There are no tables matching: {self.db_table_name}")

        logger.info("Verifying that the new table exists.")
        cursor.execute(f"SELECT * FROM information_schema.tables WHERE table_name = '{self.temp_db_table_name}'")
        temp_tables = cursor.fetchall()
        if len(temp_tables) == 0:
            raise ValueError(f"There are no tables matching: {self.temp_db_table_name}")

    def validate_indexes(self, cursor):
        logger.info("Verifying that the same number of indexes exist for the old and new table.")
        cursor.execute(f"SELECT * FROM pg_indexes WHERE tablename = '{self.temp_db_table_name}'")
        temp_indexes = ordered_dictionary_fetcher(cursor)
        self.query_result_lookup["temp_table_indexes"] = temp_indexes
        cursor.execute(f"SELECT * FROM pg_indexes WHERE tablename = '{self.db_table_name}'")
        curr_indexes = ordered_dictionary_fetcher(cursor)
        self.query_result_lookup["curr_table_indexes"] = curr_indexes
        if len(temp_indexes) != len(curr_indexes):
            raise ValueError(
                f"The number of indexes are different for the tables: {self.temp_db_table_name} and {self.db_table_name}"
            )

        logger.info("Verifying that the indexes are the same except for '_temp' in the index and table name.")
        temp_indexes = [
            {"indexname": val["indexname"].replace("_temp", ""), "indexdef": val["indexdef"].replace("_temp", "")}
            for val in temp_indexes
        ]
        curr_index_names = [val["indexname"] for val in curr_indexes]
        curr_index_defs = [val["indexdef"] for val in curr_indexes]
        for index in temp_indexes:
            if index["indexname"] not in curr_index_names or index["indexdef"] not in curr_index_defs:
                raise ValueError(
                    f"The index definitions are different for the tables: {self.temp_db_table_name} and {self.db_table_name}"
                )

    def validate_foreign_keys(self, cursor):
        logger.info("Verifying that Foreign Key constraints are not found.")
        cursor.execute(
            f"SELECT * FROM information_schema.table_constraints"
            f" WHERE table_name IN ('{self.temp_db_table_name}', '{self.db_table_name}')"
            f" AND constraint_type = 'FOREIGN KEY'"
        )
        constraints = cursor.fetchall()
        if len(constraints) > 0:
            raise ValueError(
                f"Foreign Key constraints are not allowed on '{self.temp_db_table_name}' or '{self.db_table_name}'."
                " It is advised to not allow Foreign Key constraints on swapped tables to avoid potential deadlock."
                " However, if needed they can be allowed with the `--allow-foreign-key` flag."
            )

    def validate_constraints(self, cursor):
        # Used to sort constraints for comparison since sorting in the original SQL query that retrieves them
        # would not be taking into account that some would have "_temp" appended
        def _sort_key(val):
            return val["constraint_name"]

        logger.info("Verifying that the same number of constraints exist for the old and new table.")
        cursor.execute(
            f"SELECT table_constraints.constraint_name, table_constraints.constraint_type, check_constraints.check_clause, referential_constraints.unique_constraint_name"
            f" FROM information_schema.table_constraints"
            f" LEFT OUTER JOIN information_schema.check_constraints ON (table_constraints.constraint_name = check_constraints.constraint_name)"
            f" LEFT OUTER JOIN information_schema.referential_constraints ON (table_constraints.constraint_name = referential_constraints.constraint_name)"
            f" WHERE table_name = '{self.temp_db_table_name}'"
        )
        temp_constraints = ordered_dictionary_fetcher(cursor)
        self.query_result_lookup["temp_table_constraints"] = temp_constraints
        cursor.execute(
            f"SELECT table_constraints.constraint_name, table_constraints.constraint_type, check_constraints.check_clause, referential_constraints.unique_constraint_name"
            f" FROM information_schema.table_constraints"
            f" LEFT OUTER JOIN information_schema.check_constraints ON (table_constraints.constraint_name = check_constraints.constraint_name)"
            f" LEFT OUTER JOIN information_schema.referential_constraints ON (table_constraints.constraint_name = referential_constraints.constraint_name)"
            f" WHERE table_name = '{self.db_table_name}'"
        )
        curr_constraints = ordered_dictionary_fetcher(cursor)
        self.query_result_lookup["curr_table_constraints"] = curr_constraints
        if len(temp_constraints) != len(curr_constraints):
            raise ValueError(
                f"The number of constraints are different for the tables: {self.temp_db_table_name} and {self.db_table_name}."
            )

        logger.info("Verifying that the constraints are the same except for '_temp' in the name.")
        temp_constraints = [
            {
                "constraint_name": val["constraint_name"].replace("_temp", ""),
                "constraint_type": val["constraint_type"],
                "check_clause": val["check_clause"],
                "unique_constraint_name": val["unique_constraint_name"],
            }
            for val in temp_constraints
        ]
        curr_constraints = [
            {
                "constraint_name": val["constraint_name"],
                "constraint_type": val["constraint_type"],
                "check_clause": val["check_clause"],
                "unique_constraint_name": val["unique_constraint_name"],
            }
            for val in curr_constraints
        ]
        if sorted(temp_constraints, key=_sort_key) != sorted(curr_constraints, key=_sort_key):
            raise ValueError(
                f"The constraint definitions are different for the tables: {self.temp_db_table_name} and {self.db_table_name}."
            )

    def validate_columns(self, cursor):
        logger.info("Verifying that the same number of columns exist for the old and new table.")
        columns_to_compare = [
            "column_name",
            "is_nullable",
            "data_type",
            "character_maximum_length",
            "character_octet_length",
            "numeric_precision",
            "numeric_precision_radix",
            "numeric_scale",
            "datetime_precision",
            "udt_name",
        ]
        cursor.execute(
            f"SELECT {','.join(columns_to_compare)} FROM information_schema.columns WHERE table_name = '{self.temp_db_table_name}' ORDER BY column_name"
        )
        temp_columns = ordered_dictionary_fetcher(cursor)
        cursor.execute(
            f"SELECT {','.join(columns_to_compare)} FROM information_schema.columns WHERE table_name = '{self.db_table_name}' ORDER BY column_name"
        )
        curr_columns = ordered_dictionary_fetcher(cursor)
        if len(temp_columns) != len(curr_columns):
            raise ValueError(
                f"The number of columns are different for the tables: {self.temp_db_table_name} and {self.db_table_name}."
            )

        logger.info("Verifying that the columns are the same.")
        if temp_columns != curr_columns:
            raise ValueError(
                f"The column definitions are different for the tables: {self.temp_db_table_name} and {self.db_table_name}."
            )

    def validate_state_of_tables(self, cursor, options):
        logger.info(f"Running validation to swap: {self.db_table_name} with {self.temp_db_table_name}.")

        self.validate_tables(cursor)
        self.validate_indexes(cursor)
        if not options["allow_foreign_key"]:
            self.validate_foreign_keys(cursor)
        self.validate_constraints(cursor)
        self.validate_columns(cursor)
