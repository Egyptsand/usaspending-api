FORMAT: 1A
HOST: https://api.usaspending.gov

# Recipients [/api/v2/agency/{toptier_code}/recipients/{?fiscal_year}]

Deprecated: This endpoint will be removed in the near future.
Returns a list of data points of an agencies recipients for a given fiscal year

## GET
+ Parameters
    + `toptier_code`: 086 (required, string)
        The toptier code of an agency (could be a CGAC or FREC) so only numeric character strings of length 3-4 are accepted.
    + `fiscal_year` (optional, number)
        The desired appropriations fiscal year. Defaults to the current FY.

+ Response 200 (application/json)
    + Attributes
        + `toptier_code` (required, string)
        + `fiscal_year` (required, number)
        + `count` (required, number)
            The number of recipients that received awards from this agency in the provided fiscal year
        + `total_federal_count` (required, number)
            The number of receipients that received awards from any agency in the provided fiscal year
        + `max` (required, number)
        + `min` (required, number)
        + `25th_percentile` (required, number)
        + `50th_percentile` (required, number)
        + `75th_percentile` (required, number)
        + `messages` (required, array[string], fixed-type)
            An array of warnings or instructional directives to aid consumers of this endpoint with development and debugging.

    + Body

            {
                "toptier_code": "015",
                "fiscal_year": 2021,
                "count": 4,
                "total_federal_count": 27,
                "max": 450000.0,
                "min": 21532.0,
                "25th_percentile": 21532.0,
                "50th_percentile": 34029.61,
                "75th_percentile": 168000.0,
                "messages": []
            }
