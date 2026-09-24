import json


def parse_busydata(body):
    """
    Parse Google Maps /maps/preview/place response body
    and return popular/busy time data.

    Returns:
        list[dict]:
        [
            {
                "weekday": 7,
                "hour": 11,
                "busy": 71
            },
            ...
        ]
    """

    # --------------------------------------------------
    # 1. Remove Google's XSSI prefix
    # --------------------------------------------------
    if isinstance(body, bytes):
        body = body.decode("utf-8")

    body = body.strip()

    if body.startswith(")]}'"):
        body = body.split("\n", 1)[1]

    # --------------------------------------------------
    # 2. Parse JSON
    # --------------------------------------------------
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid Google Maps JSON: {e}")

    # --------------------------------------------------
    # 3. Find the 7-day busy-data structure
    # --------------------------------------------------
    busy_days = _find_busy_days(data)

    if busy_days is None:
        return []

    # --------------------------------------------------
    # 4. Convert to simple records
    # --------------------------------------------------
    result = []

    for day in busy_days:
        weekday = day[0]
        hours = day[1]

        for row in hours:
            if not isinstance(row, list) or len(row) < 2:
                continue

            hour = row[0]
            busy = row[1]

            # Only accept valid hour/busy values
            if not isinstance(hour, (int, float)):
                continue

            if not 0 <= hour <= 23:
                continue

            if not isinstance(busy, (int, float)):
                continue

            if not 0 <= busy <= 100:
                continue

            result.append({
                "weekday": int(weekday),
                "hour": int(hour),
                "busy": int(busy)
            })

    return result


def _find_busy_days(obj):
    """
    Recursively search Google Maps JSON for the
    7-day busy-time structure.

    Expected structure:

    [
        [7, [hour rows...], 0],
        [1, [hour rows...], 0],
        ...
        [6, [hour rows...], 0]
    ]
    """

    if isinstance(obj, list):

        # Check whether this list itself looks like
        # the 7-day busy-time structure.
        if _is_busy_days(obj):
            return obj

        # Otherwise search recursively
        for item in obj:
            result = _find_busy_days(item)

            if result is not None:
                return result

    return None


def _is_busy_days(obj):
    """Check whether obj looks like Google's 7-day busy data."""

    if not isinstance(obj, list):
        return False

    if len(obj) != 7:
        return False

    weekdays = []

    for day in obj:

        if not isinstance(day, list):
            return False

        if len(day) < 2:
            return False

        weekday = day[0]
        hours = day[1]

        # Google weekday numbering:
        # 1 = Monday ... 6 = Saturday, 7 = Sunday
        if weekday not in {1, 2, 3, 4, 5, 6, 7}:
            return False

        if weekday in weekdays:
            return False

        if not isinstance(hours, list):
            return False

        weekdays.append(weekday)

        # Check hour rows
        for row in hours:

            if not isinstance(row, list):
                return False

            if len(row) < 2:
                return False

            hour = row[0]
            busy = row[1]

            if not isinstance(hour, (int, float)):
                return False

            if not 0 <= hour <= 23:
                return False

            if not isinstance(busy, (int, float)):
                return False

            if not 0 <= busy <= 100:
                return False

    return set(weekdays) == {1, 2, 3, 4, 5, 6, 7}