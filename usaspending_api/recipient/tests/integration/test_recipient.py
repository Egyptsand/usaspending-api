import datetime
import pytest

from model_mommy import mommy
from rest_framework import status
from uuid import UUID
from unittest.mock import Mock

from usaspending_api.common.exceptions import InvalidParameterException
from usaspending_api.recipient.v2.views import recipients

# Getting relative dates as the 'latest'/default argument returns results relative to when it gets called
from usaspending_api.search.tests.data.utilities import setup_elasticsearch_test

TODAY = datetime.datetime.now()
INSIDE_OF_LATEST = TODAY - datetime.timedelta(365 - 2)

TEST_REF_COUNTRY_CODE = {
    "PARENT COUNTRY CODE": {"country_code": "PARENT COUNTRY CODE", "country_name": "PARENT COUNTRY NAME"},
    "CHILD COUNTRY CODE": {"country_code": "CHILD COUNTRY CODE", "country_name": "CHILD COUNTRY NAME"},
}
MAP_DUNS_TO_CONTRACT = {
    "address_line_1": "address_line1",
    "address_line_2": "address_line2",
    "city": "city_name",
    "congressional_district": "congressional_code",
    "state": "state_code",
    "zip5": "zip",
}

TEST_DUNS = {
    "000000001": {
        "awardee_or_recipient_uniqu": "000000001",
        "legal_business_name": "PARENT RECIPIENT",
        "address_line_1": "PARENT ADDRESS LINE 1",
        "address_line_2": "PARENT ADDRESS LINE 2",
        "city": "PARENT CITY",
        "congressional_district": "PARENT CONGRESSIONAL DISTRICT",
        "country_code": "PARENT COUNTRY CODE",
        "state": "PARENT STATE",
        "zip": "PARENT ZIP",
        "zip4": "PARENT ZIP4",
        "business_types_codes": ["2X"],
        "uei": "AAAAAAAAAAAA",
    },
    "000000002": {
        "awardee_or_recipient_uniqu": "000000002",
        "legal_business_name": "CHILD RECIPIENT",
        "address_line_1": "CHILD ADDRESS LINE 1",
        "address_line_2": "CHILD ADDRESS LINE 2",
        "city": "CHILD CITY",
        "congressional_district": "CHILD CONGRESSIONAL DISTRICT",
        "country_code": "CHILD COUNTRY CODE",
        "state": "CHILD STATE",
        "zip": "CHILD ZIP",
        "zip4": "CHILD ZIP4",
        "business_types_codes": ["A8"],
    },
}
TEST_RECIPIENT_LOCATIONS = {
    "88a7d62e-d9e6-a7c6-8a1e-2a52a59fb9f2": {
        "address_line_1": "PARENT ADDRESS LINE 1",
        "address_line_2": "PARENT ADDRESS LINE 2",
        "city": "PARENT CITY",
        "congressional_district": "PARENT CONGRESSIONAL DISTRICT",
        "country_code": "PARENT COUNTRY CODE",
        "state": "PARENT STATE",
        "zip5": "PARENT ZIP",
        "zip4": "PARENT ZIP4",
    },
    "083ac6fa-3d08-8d35-79da-b658a84260df": {
        "address_line_1": "CHILD ADDRESS LINE 1",
        "address_line_2": "CHILD ADDRESS LINE 2",
        "city": "CHILD CITY",
        "congressional_district": "CHILD CONGRESSIONAL DISTRICT",
        "country_code": "CHILD COUNTRY CODE",
        "state": "CHILD STATE",
        "zip5": "CHILD ZIP",
        "zip4": "CHILD ZIP4",
    },
    "cd6ac2ed-8d2d-2c2e-4934-710eb82100f3": {
        "address_line_1": "OTHER ADDRESS LINE 1",
        "address_line_2": "OTHER ADDRESS LINE 2",
        "city": "OTHER CITY",
        "congressional_district": "OTHER CONGRESSIONAL DISTRICT",
        "country_code": "OTHER COUNTRY CODE",
        "state": "OTHER STATE",
        "zip5": "OTHER ZIP",
        "zip4": "OTHER ZIP4",
    },
    "6dffe44a-554c-26b4-b7ef-44db50083732": {
        "address_line_1": None,
        "address_line_2": None,
        "city": None,
        "congressional_district": None,
        "country_code": None,
        "state": None,
        "zip5": None,
        "zip4": None,
    },
}
TEST_RECIPIENT_LOOKUPS = {
    "88a7d62e-d9e6-a7c6-8a1e-2a52a59fb9f2": {
        "recipient_hash": "88a7d62e-d9e6-a7c6-8a1e-2a52a59fb9f2",
        "duns": "000000001",
        "uei": "AAAAAAAAAAAA",
        "legal_business_name": "PARENT RECIPIENT",
    },
    "083ac6fa-3d08-8d35-79da-b658a84260df": {
        "recipient_hash": "083ac6fa-3d08-8d35-79da-b658a84260df",
        "duns": "000000002",
        "uei": "BBBBBBBBBBBB",
        "legal_business_name": "CHILD RECIPIENT",
    },
    "cd6ac2ed-8d2d-2c2e-4934-710eb82100f3": {
        "recipient_hash": "cd6ac2ed-8d2d-2c2e-4934-710eb82100f3",
        "duns": None,
        "uei": "",
        "legal_business_name": "OTHER RECIPIENT",
    },
    "6dffe44a-554c-26b4-b7ef-44db50083732": {
        "recipient_hash": "6dffe44a-554c-26b4-b7ef-44db50083732",
        "duns": None,
        "uei": "",
        "legal_business_name": "MULTIPLE RECIPIENTS",
    },
}
for hash, recipient in TEST_RECIPIENT_LOOKUPS.items():
    recipient.update(TEST_RECIPIENT_LOCATIONS[hash])

TEST_RECIPIENT_PROFILES = {
    # Parent Recipient, including non-existent child duns
    "88a7d62e-d9e6-a7c6-8a1e-2a52a59fb9f2-P": {
        "recipient_level": "P",
        "recipient_hash": "88a7d62e-d9e6-a7c6-8a1e-2a52a59fb9f2",
        "recipient_unique_id": "000000001",
        "recipient_name": "PARENT RECIPIENT",
        "recipient_affiliations": ["000000001", "000000002", "000000005"],
        "uei": "AAAAAAAAAAAA",
    },
    # Child Recipient 1 - lists itself as both parent and child
    "88a7d62e-d9e6-a7c6-8a1e-2a52a59fb9f2-C": {
        "recipient_level": "C",
        "recipient_hash": "88a7d62e-d9e6-a7c6-8a1e-2a52a59fb9f2",
        "recipient_unique_id": "000000001",
        "recipient_name": "PARENT RECIPIENT",
        "recipient_affiliations": ["000000001"],
        "uei": "AAAAAAAAAAAA",
    },
    # Child Recipient 2 - different from parent duns
    "083ac6fa-3d08-8d35-79da-b658a84260df-C": {
        "recipient_level": "C",
        "recipient_hash": "083ac6fa-3d08-8d35-79da-b658a84260df",
        "recipient_unique_id": "000000002",
        "recipient_name": "CHILD RECIPIENT",
        "recipient_affiliations": ["000000001"],
        "uei": "BBBBBBBBBBBB",
    },
    # Other Recipient
    "cd6ac2ed-8d2d-2c2e-4934-710eb82100f3-R": {
        "recipient_level": "R",
        "recipient_hash": "cd6ac2ed-8d2d-2c2e-4934-710eb82100f3",
        "recipient_unique_id": None,
        "recipient_name": "OTHER RECIPIENT",
        "recipient_affiliations": [],
        "uei": "BBBBBBBBBBBB",
    },
}
TEST_SUMMARY_TRANSACTION_NORMALIZED_FOR_FPDS = {
    "latest": {"action_date": INSIDE_OF_LATEST, "federal_action_obligation": 100},
    "FY2016": {"action_date": datetime.datetime(2015, 10, 1), "federal_action_obligation": 50},
    "FY2008": {"action_date": datetime.datetime(2007, 10, 1), "federal_action_obligation": 200},
}
TEST_SUMMARY_TRANSACTION_NORMALIZED_FOR_FABS = {
    "latest": {"action_date": INSIDE_OF_LATEST, "face_value_loan_guarantee": 1000, "type": "07"},
    "FY2016": {"action_date": datetime.datetime(2015, 10, 1), "face_value_loan_guarantee": 500, "type": "08"},
    "FY2008": {"action_date": datetime.datetime(2007, 10, 1), "face_value_loan_guarantee": 2000, "type": "08"},
}
TEST_SUMMARY_TRANSACTION_RECIPIENT = {
    "latest": {
        "awardee_or_recipient_legal": "PARENT RECIPIENT",
        "awardee_or_recipient_uniqu": "000000001",
        "ultimate_parent_unique_ide": "000000001",
        "awardee_or_recipient_uei": "AAAAAAAAAAAA",
    },
    "FY2016": {
        "awardee_or_recipient_legal": "CHILD RECIPIENT",
        "awardee_or_recipient_uniqu": "000000002",
        "ultimate_parent_unique_ide": "000000001",
        "awardee_or_recipient_uei": "BBBBBBBBBBBB",
    },
    "FY2008": {
        "awardee_or_recipient_legal": "OTHER RECIPIENT",
        "awardee_or_recipient_uniqu": None,
        "ultimate_parent_unique_ide": None,
        "awardee_or_recipient_uei": None,
    },
}


@pytest.mark.django_db
def create_transaction_test_data(transaction_recipient_list=None):

    if transaction_recipient_list is None:
        transaction_recipient_list = TEST_SUMMARY_TRANSACTION_RECIPIENT.values()

    for count, transaction_normalized in enumerate(TEST_SUMMARY_TRANSACTION_NORMALIZED_FOR_FPDS.values(), 1):
        base_transaction_normalized = {
            "id": count,
            "award_id": count,
            "is_fpds": True,
            "business_categories": ["expected", "business", "cat"],
        }
        base_transaction_normalized.update(transaction_normalized)
        mommy.make("awards.Award", id=count, latest_transaction_id=count)
        mommy.make("awards.TransactionNormalized", **base_transaction_normalized)

    for count, transaction_fpds in enumerate(transaction_recipient_list, 1):
        base_transaction_fpds = {"transaction_id": count}
        base_transaction_fpds.update(transaction_fpds)
        mommy.make("awards.TransactionFPDS", **base_transaction_fpds)

    for count, transaction_normalized in enumerate(
        TEST_SUMMARY_TRANSACTION_NORMALIZED_FOR_FABS.values(), len(TEST_SUMMARY_TRANSACTION_NORMALIZED_FOR_FPDS) + 1
    ):
        base_transaction_normalized = {
            "id": count,
            "award_id": count,
            "is_fpds": False,
            "business_categories": ["expected", "business", "cat"],
        }
        base_transaction_normalized.update(transaction_normalized)
        mommy.make("awards.Award", id=count, latest_transaction_id=count)
        mommy.make("awards.TransactionNormalized", **base_transaction_normalized)

    for count, transaction_fabs in enumerate(
        transaction_recipient_list, len(TEST_SUMMARY_TRANSACTION_NORMALIZED_FOR_FPDS) + 1
    ):
        base_transaction_fabs = {"transaction_id": count}
        base_transaction_fabs.update(transaction_fabs)
        base_transaction_fabs["uei"] = base_transaction_fabs["awardee_or_recipient_uei"]
        del base_transaction_fabs["awardee_or_recipient_uei"]
        mommy.make("awards.TransactionFABS", **base_transaction_fabs)


@pytest.mark.django_db
def create_recipient_profile_test_data(*recipient_profile_list):
    for recipient_profile in recipient_profile_list:
        mommy.make("recipient.RecipientProfile", **recipient_profile)


@pytest.mark.django_db
def create_recipient_lookup_test_data(*recipient_lookup_list):
    for recipient_lookup in recipient_lookup_list:
        mommy.make("recipient.RecipientLookup", **recipient_lookup)


@pytest.mark.django_db
def test_validate_recipient_id_success():
    """ Testing a run of a valid recipient id """
    recipient_id = "88a7d62e-d9e6-a7c6-8a1e-2a52a59fb9f2-P"
    mommy.make("recipient.RecipientProfile", **TEST_RECIPIENT_PROFILES[recipient_id])

    expected_hash = recipient_id[:-2]
    expected_level = recipient_id[-1]
    try:
        recipient_hash, recipient_level = recipients.validate_recipient_id(recipient_id)
        assert recipient_hash == expected_hash
        assert recipient_level == expected_level
    except InvalidParameterException:
        assert False


@pytest.mark.django_db
def test_validate_recipient_id_failures():
    """ Testing a run of invalid recipient ids """
    recipient_id = "88a7d62e-d9e6-a7c6-8a1e-2a52a59fb9f2-P"
    mommy.make("recipient.RecipientProfile", **TEST_RECIPIENT_PROFILES[recipient_id])

    def call_validate_recipient_id(recipient_id):
        try:
            recipients.validate_recipient_id(recipient_id)
            return False
        except InvalidParameterException:
            return True

    # Test with no dashes
    recipient_id = "broken_recipient_id"
    assert call_validate_recipient_id(recipient_id) is True

    # Test with invalid recipient level
    recipient_id = "broken_recipient-id"
    assert call_validate_recipient_id(recipient_id) is True

    # Test with invalid hash
    recipient_id = "broken_recipient-R"
    assert call_validate_recipient_id(recipient_id) is True

    # Test with id not available
    recipient_id = "00002940-fdbe-3fc5-9252-000000-R"
    assert call_validate_recipient_id(recipient_id) is True


@pytest.mark.django_db
def test_extract_duns_uei_name_from_hash():
    """ Testing extracting name and duns from the recipient hash """
    recipient_hash = "88a7d62e-d9e6-a7c6-8a1e-2a52a59fb9f2"
    mommy.make("recipient.RecipientLookup", **TEST_RECIPIENT_LOOKUPS[recipient_hash])

    expected_duns = TEST_RECIPIENT_LOOKUPS[recipient_hash]["duns"]
    expected_uei = TEST_RECIPIENT_LOOKUPS[recipient_hash]["uei"]
    expected_name = TEST_RECIPIENT_LOOKUPS[recipient_hash]["legal_business_name"]
    duns, uei, name = recipients.extract_duns_uei_name_from_hash(recipient_hash)
    assert duns == expected_duns
    assert uei == expected_uei
    assert name == expected_name


@pytest.mark.django_db
def test_extract_parent_from_hash():
    """ Testing extracting parent duns/name from recipient hash"""
    # This one specifically has to be a child
    recipient_id = "083ac6fa-3d08-8d35-79da-b658a84260df-C"
    recipient_hash = TEST_RECIPIENT_PROFILES[recipient_id]["recipient_hash"]
    mommy.make("recipient.RecipientProfile", **TEST_RECIPIENT_PROFILES[recipient_id])

    expected_parent_id = "88a7d62e-d9e6-a7c6-8a1e-2a52a59fb9f2-P"
    parent_hash = expected_parent_id[:-2]
    mommy.make("recipient.RecipientLookup", **TEST_RECIPIENT_LOOKUPS[parent_hash])

    expected_name = TEST_RECIPIENT_LOOKUPS[parent_hash]["legal_business_name"]
    expected_duns = TEST_RECIPIENT_LOOKUPS[parent_hash]["duns"]
    parents = recipients.extract_parents_from_hash(recipient_hash)
    assert expected_duns == parents[0]["parent_duns"]
    assert expected_name == parents[0]["parent_name"]
    assert expected_parent_id == parents[0]["parent_id"]


@pytest.mark.django_db
def test_extract_parent_from_hash_failure():
    """Testing extracting parent duns/name from recipient hash but with recipient lookup removed
    as there may be cases where the parent recipient is not found/listed
    """
    # This one specifically has to be a child
    recipient_id = "083ac6fa-3d08-8d35-79da-b658a84260df-C"
    recipient_hash = TEST_RECIPIENT_PROFILES[recipient_id]["recipient_hash"]
    mommy.make("recipient.RecipientProfile", **TEST_RECIPIENT_PROFILES[recipient_id])

    expected_name = None
    expected_duns = None
    expected_parent_id = None
    parents = recipients.extract_parents_from_hash(recipient_hash)
    assert expected_duns == parents[0]["parent_duns"]
    assert expected_name == parents[0]["parent_name"]
    assert expected_parent_id == parents[0]["parent_id"]


@pytest.mark.django_db
def test_extract_location_success():
    """ Testing extracting location data from recipient hash using the DUNS table """
    recipient_hash = "88a7d62e-d9e6-a7c6-8a1e-2a52a59fb9f2"
    mommy.make("recipient.RecipientLookup", **TEST_RECIPIENT_LOOKUPS[recipient_hash])
    country_code = TEST_RECIPIENT_LOCATIONS[recipient_hash]["country_code"]
    mommy.make("references.RefCountryCode", **TEST_REF_COUNTRY_CODE[country_code])

    additional_blank_fields = ["address_line3", "foreign_province", "county_name", "foreign_postal_code"]
    expected_location = TEST_RECIPIENT_LOCATIONS[recipient_hash].copy()
    expected_location["country_name"] = TEST_REF_COUNTRY_CODE[country_code]["country_name"]
    for additional_blank_field in additional_blank_fields:
        expected_location[additional_blank_field] = None
    for k in MAP_DUNS_TO_CONTRACT:
        expected_location[MAP_DUNS_TO_CONTRACT[k]] = expected_location[k]
        del expected_location[k]
    location = recipients.extract_location(recipient_hash)
    assert location == expected_location


@pytest.mark.django_db
def test_cleanup_location():
    """ Testing cleaning up the location data """

    # Test United States fix
    test_location = {"country_code": "UNITED STATES"}
    assert {"country_code": "USA", "country_name": None} == recipients.cleanup_location(test_location)

    # Test Country_Code
    mommy.make("references.RefCountryCode", country_code="USA", country_name="UNITED STATES")
    test_location = {"country_code": "USA"}
    assert {"country_code": "USA", "country_name": "UNITED STATES"} == recipients.cleanup_location(test_location)

    # Test Congressional Codes
    test_location = {"congressional_code": "CA13"}
    assert {"congressional_code": "13"} == recipients.cleanup_location(test_location)
    test_location = {"congressional_code": "13.0"}
    assert {"congressional_code": "13"} == recipients.cleanup_location(test_location)


@pytest.mark.django_db
def test_extract_business_categories(monkeypatch):
    """ Testing extracting business categories from the recipient name/duns """
    recipient_hash = "88a7d62e-d9e6-a7c6-8a1e-2a52a59fb9f2"
    recipient_name = TEST_RECIPIENT_LOOKUPS[recipient_hash]["legal_business_name"]
    recipient_duns = TEST_RECIPIENT_LOOKUPS[recipient_hash]["duns"]
    business_categories = ["le", "business", "cat"]

    utm_objects = Mock()
    utm_objects.filter().order_by().values().first.return_value = {"business_categories": business_categories}
    monkeypatch.setattr("usaspending_api.search.models.TransactionSearch.objects", utm_objects)

    mommy.make("recipient.RecipientLookup", **TEST_RECIPIENT_LOOKUPS[recipient_hash])

    # Mock DUNS
    # Should add 'category_business'
    mommy.make("recipient.DUNS", **TEST_DUNS[recipient_duns])

    expected_business_cat = business_categories + ["category_business"]
    business_cat = recipients.extract_business_categories(recipient_name, recipient_duns, recipient_hash)
    # testing for equality-only, order unnecessary
    assert sorted(business_cat) == sorted(expected_business_cat)


@pytest.mark.django_db
def test_extract_business_categories_special():
    """ Testing extracting the business categories for a special case  """
    recipient_name = "MULTIPLE RECIPIENTS"
    recipient_duns = None
    recipient_hash = ""
    business_categories = recipients.extract_business_categories(recipient_name, recipient_duns, recipient_hash)
    assert business_categories == []


@pytest.mark.django_db
def test_obtain_recipient_totals_year(monkeypatch, elasticsearch_transaction_index):
    """ Testing recipient totals with different year values """
    # Testing with specific child
    recipient_id = "083ac6fa-3d08-8d35-79da-b658a84260df-C"
    recipient_hash = recipient_id[:-2]

    # load all of the transactions
    transaction_recipient_data = {
        "awardee_or_recipient_legal": "CHILD RECIPIENT",
        "awardee_or_recipient_uniqu": "000000002",
        "awardee_or_recipient_uei": "BBBBBBBBBBBB",
        "ultimate_parent_unique_ide": "000000001",
    }
    create_transaction_test_data([transaction_recipient_data] * len(TEST_SUMMARY_TRANSACTION_RECIPIENT))

    # load recipient lookup
    create_recipient_lookup_test_data(TEST_RECIPIENT_LOOKUPS[recipient_hash])

    # For latest transaction's we're pulling from recipient_profile
    associated_recipient_profile = TEST_RECIPIENT_PROFILES[recipient_id].copy()
    associated_recipient_profile["last_12_months"] = 100
    associated_recipient_profile["last_12_months_count"] = 1
    mommy.make("recipient.RecipientProfile", **associated_recipient_profile)

    setup_elasticsearch_test(monkeypatch, elasticsearch_transaction_index)

    # Latest
    results = recipients.obtain_recipient_totals(recipient_id, year="latest")
    assert results[0]["total_obligation_amount"] == 100
    assert results[0]["total_obligation_count"] == 2
    assert results[0]["total_face_value_loan_amount"] == 1000
    assert results[0]["total_face_value_loan_count"] == 1

    # All
    results = recipients.obtain_recipient_totals(recipient_id, year="all")
    assert results[0]["total_obligation_amount"] == 350
    assert results[0]["total_obligation_count"] == 6
    assert results[0]["total_face_value_loan_amount"] == 3500
    assert results[0]["total_face_value_loan_count"] == 3

    # FY2016
    results = recipients.obtain_recipient_totals(recipient_id, year="2016")
    assert results[0]["total_obligation_amount"] == 50
    assert results[0]["total_obligation_count"] == 2
    assert results[0]["total_face_value_loan_amount"] == 500
    assert results[0]["total_face_value_loan_count"] == 1


@pytest.mark.django_db
def test_obtain_recipient_totals_parent(monkeypatch, elasticsearch_transaction_index):
    """ Testing recipient totals with parent child relationships """
    # Testing with specific parent/child ids
    parent_id = "88a7d62e-d9e6-a7c6-8a1e-2a52a59fb9f2-P"

    # load recipient profiles
    for recipient_id, recipient_profile in TEST_RECIPIENT_PROFILES.items():
        mommy.make("recipient.RecipientProfile", **recipient_profile)

    # load transactions for each child and parent (making sure it's excluded)
    create_transaction_test_data()

    # load recipient lookup
    create_recipient_lookup_test_data(*TEST_RECIPIENT_LOOKUPS.values())

    setup_elasticsearch_test(monkeypatch, elasticsearch_transaction_index)

    results = recipients.obtain_recipient_totals(parent_id, year="all")
    assert results[0]["total_obligation_amount"] == 150
    assert results[0]["total_obligation_count"] == 4
    assert results[0]["total_face_value_loan_amount"] == 1500
    assert results[0]["total_face_value_loan_count"] == 2


def recipient_overview_endpoint(id, year="latest"):
    endpoint = "/api/v2/recipient/duns/{}/".format(id)
    if year:
        endpoint = "{}?year={}".format(endpoint, year)
    return endpoint


@pytest.mark.django_db
def test_recipient_overview(client, monkeypatch, elasticsearch_transaction_index):
    """ Testing a simple example of the endpoint as a whole """
    r_id = "88a7d62e-d9e6-a7c6-8a1e-2a52a59fb9f2-C"

    # Mock Transactions
    create_transaction_test_data()

    # Mock Recipient Profiles
    for recipient_id, recipient_profile in TEST_RECIPIENT_PROFILES.items():
        recipient_profile_copy = recipient_profile.copy()
        if recipient_id == r_id:
            recipient_profile_copy["last_12_months"] = 100
            recipient_profile_copy["last_12_months_count"] = 1
        mommy.make("recipient.RecipientProfile", **recipient_profile_copy)

    # Mock Recipient Lookups
    create_recipient_lookup_test_data(*TEST_RECIPIENT_LOOKUPS.values())

    # Mock DUNS - should add `category-business`
    for duns, duns_dict in TEST_DUNS.items():
        test_duns_model = duns_dict.copy()
        country_code = test_duns_model["country_code"]
        mommy.make("recipient.DUNS", **test_duns_model)
        mommy.make("references.RefCountryCode", **TEST_REF_COUNTRY_CODE[country_code])

    setup_elasticsearch_test(monkeypatch, elasticsearch_transaction_index)

    resp = client.get(recipient_overview_endpoint(r_id))
    assert resp.status_code == status.HTTP_200_OK
    expected = {
        "name": "PARENT RECIPIENT",
        "alternate_names": [],
        "duns": "000000001",
        "uei": "AAAAAAAAAAAA",
        "recipient_id": "88a7d62e-d9e6-a7c6-8a1e-2a52a59fb9f2-C",
        "recipient_level": "C",
        "parent_name": "PARENT RECIPIENT",
        "parent_duns": "000000001",
        "parent_id": "88a7d62e-d9e6-a7c6-8a1e-2a52a59fb9f2-P",
        "parent_uei": "AAAAAAAAAAAA",
        "parents": [
            {
                "parent_duns": "000000001",
                "parent_id": "88a7d62e-d9e6-a7c6-8a1e-2a52a59fb9f2-P",
                "parent_name": "PARENT RECIPIENT",
                "parent_uei": "AAAAAAAAAAAA",
            }
        ],
        "business_types": sorted(["expected", "business", "cat"] + ["category_business"]),
        "location": {
            "address_line1": "PARENT ADDRESS LINE 1",
            "address_line2": "PARENT ADDRESS LINE 2",
            "address_line3": None,
            "county_name": None,
            "city_name": "PARENT CITY",
            "congressional_code": "PARENT CONGRESSIONAL DISTRICT",
            "country_code": "PARENT COUNTRY CODE",
            "country_name": "PARENT COUNTRY NAME",
            "state_code": "PARENT STATE",
            "zip": "PARENT ZIP",
            "zip4": "PARENT ZIP4",
            "foreign_province": None,
            "foreign_postal_code": None,
        },
        "total_transaction_amount": 100,
        "total_transactions": 2,
        "total_face_value_loan_amount": 1000,
        "total_face_value_loan_transactions": 1,
    }
    # testing for equality-only, order unnecessary
    resp.data["business_types"] = sorted(resp.data["business_types"])
    assert resp.data == expected


@pytest.mark.django_db
def test_extract_hash_from_duns_or_uei_via_duns():
    """ Testing extracting the hash/name from a DUNS """
    example_duns = "000000001"
    expected_hash = "88a7d62e-d9e6-a7c6-8a1e-2a52a59fb9f2"
    expected_name = "PARENT RECIPIENT"
    mommy.make("recipient.RecipientLookup", **TEST_RECIPIENT_LOOKUPS[expected_hash])

    recipient_hash = recipients.extract_hash_from_duns_or_uei(example_duns)
    assert UUID(expected_hash) == recipient_hash


@pytest.mark.django_db
def test_extract_hash_from_duns_or_uei_via_uei():
    """ Testing extracting the hash/name from a DUNS """
    example_uei = "AAAAAAAAAAAA"
    expected_hash = "00077a9a-5a70-8919-fd19-330762af6b84"
    mommy.make("recipient.RecipientLookup", **TEST_RECIPIENT_LOOKUPS[expected_hash])

    recipient_hash = recipients.extract_hash_from_duns_or_uei(example_uei)
    assert UUID(expected_hash) == recipient_hash


def recipient_children_endpoint(duns, year="latest"):
    endpoint = "/api/v2/recipient/children/{}/".format(duns)
    if year:
        endpoint = "{}?year={}".format(endpoint, year)
    return endpoint


@pytest.mark.django_db
def test_child_recipient_success(client, monkeypatch, elasticsearch_transaction_index):
    """ Testing successful child recipient calls """
    child1_id = "88a7d62e-d9e6-a7c6-8a1e-2a52a59fb9f2-C"
    parent_child1_duns = "000000001"
    child2_id = "083ac6fa-3d08-8d35-79da-b658a84260df-C"
    child2_duns = "000000002"

    # Mock Recipient Profiles
    create_recipient_profile_test_data(*TEST_RECIPIENT_PROFILES.values())

    # Mock Recipient Lookups
    create_recipient_lookup_test_data(*TEST_RECIPIENT_LOOKUPS.values())

    # Mock Transactions
    create_transaction_test_data()

    setup_elasticsearch_test(monkeypatch, elasticsearch_transaction_index)

    # Ignoring nonexistent child hash - 00eadaa1-6e1f-22f2-419b-e5894374db96
    child1_object = {
        "recipient_id": child1_id,
        "name": "PARENT RECIPIENT",
        "duns": parent_child1_duns,
        "uei": "AAAAAAAAAAAA",
        "amount": 100,
        "state_province": "PARENT STATE",
    }
    child2_object = {
        "recipient_id": child2_id,
        "name": "CHILD RECIPIENT",
        "duns": child2_duns,
        "uei": "BBBBBBBBBBBB",
        "amount": 50,
        "state_province": "CHILD STATE",
    }
    expected = [child2_object, child1_object]
    resp = client.get(recipient_children_endpoint(parent_child1_duns, "all"))
    assert resp.status_code == status.HTTP_200_OK
    # testing for equality-only, order unnecessary
    assert sorted(resp.data, key=lambda key: key["recipient_id"]) == expected


@pytest.mark.django_db
def test_child_recipient_failures(client):
    """ Testing failed child recipient calls """
    # Mock Recipient Profiles
    create_recipient_profile_test_data(*TEST_RECIPIENT_PROFILES.values())

    # Mock Recipient Lookups
    create_recipient_lookup_test_data(*TEST_RECIPIENT_LOOKUPS.values())

    # Mock Transactions
    create_transaction_test_data()

    # Testing for non-existent DUNS
    non_existent_duns = "000000003"
    resp = client.get(recipient_children_endpoint(non_existent_duns, "all"))
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.data["detail"] == "Recipient not found: '{}'.".format(non_existent_duns)
