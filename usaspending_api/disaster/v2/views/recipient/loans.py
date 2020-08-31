import re

from typing import List

from usaspending_api.common.elasticsearch.json_helpers import json_str_to_dict
from usaspending_api.disaster.v2.views.elasticsearch_base import (
    ElasticsearchDisasterBase,
    ElasticsearchLoansPaginationMixin,
)
from usaspending_api.search.v2.elasticsearch_helper import get_summed_value_as_float


class RecipientLoansViewSet(ElasticsearchLoansPaginationMixin, ElasticsearchDisasterBase):
    """
    This route takes DEF Codes and Query text and returns Loans by Recipient.
    """

    endpoint_doc = "usaspending_api/api_contracts/contracts/v2/disaster/recipient/loans.md"

    required_filters = ["def_codes", "query", "_loan_award_type_codes"]
    query_fields = ["recipient_name"]
    agg_key = "recipient_agg_key"

    sum_column_mapping: List[str]  # Set in the pagination mixin

    def build_elasticsearch_result(self, response: dict) -> List[dict]:
        results = []
        info_buckets = response.get("group_by_agg_key", {}).get("buckets", [])
        for bucket in info_buckets:
            info = json_str_to_dict(bucket.get("key"))

            # Build a list of hash IDs to handle multiple levels
            recipient_hash = info.get("hash")
            recipient_levels = sorted(list(re.sub("[{},]", "", info.get("levels", ""))))
            if recipient_hash and recipient_levels:
                recipient_hash_list = [f"{recipient_hash}-{level}" for level in recipient_levels]
            else:
                recipient_hash_list = None

            results.append(
                {
                    "id": recipient_hash_list,
                    "code": info["unique_id"] or "DUNS Number not provided",
                    "description": info["name"] or None,
                    "award_count": int(bucket.get("doc_count", 0)),
                    **{
                        column: get_summed_value_as_float(bucket, self.sum_column_mapping[column])
                        for column in self.sum_column_mapping
                    },
                }
            )

        return results
