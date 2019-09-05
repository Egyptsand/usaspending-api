import datetime

subtier_agency_list = {}  # global variable, populated by fpds_loader


def capitalize_if_string(val):
    if isinstance(val, str):
        return val.upper()
    return val


def false_if_null(val):
    if val is None:
        return False
    return val


# TODO: replace this with cursor.morgify() in some way that doesn't need a live connection passed around everywhere
def format_value_for_sql(val):
    if isinstance(val, str):
        return "\'{}\'".format(val.replace("'", "''").replace("\"", "\"\""))
    elif val is None:
        return "null"
    elif isinstance(val, list):
        return "\'{" + (",".join(val)) + "}\'"  # noqa
    elif isinstance(val, datetime.datetime):
        return "\'{}-{}-{} {}:{}:{}\'".format(val.year, val.month, val.day, val.hour, val.minute, val.second)
    else:
        return val
