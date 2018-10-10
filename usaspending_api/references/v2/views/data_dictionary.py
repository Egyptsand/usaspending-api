import logging

from rest_framework.response import Response

from usaspending_api.common.exceptions import NoDataFoundException
from usaspending_api.common.views import APIDocumentationView
from usaspending_api.references.models import Rosetta


logger = logging.getLogger("console")


class DataDictionaryViewSet(APIDocumentationView):
    """
    endpoint_doc: /references/data_dictionary.md
    """

    def get(self, request, format=None):
        try:
            api_response = Rosetta.objects.filter(document_name="api_response").values("document")[0]
        except Exception as e:
            raise NoDataFoundException("Unable to locate and fetch a Data Dictionary object from the database")
        return Response(api_response)
