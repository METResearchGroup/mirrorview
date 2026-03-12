from datetime import datetime, timezone

timestamp_format = "%Y_%m_%d-%H:%M:%S"

def get_current_timestamp() -> str:
    """Get the current timestamp in the format YYYY_MM_DD-HH:MM:SS."""
    return datetime.now().strftime(timestamp_format)

def get_date_aware_timestamp(dt: datetime | None) -> str:
    """Get the timestamp in the format YYYY_MM_DD-HH:MM:SS, ensuring it's timezone-aware."""
    if dt is None:
        dt = datetime.now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime(timestamp_format)
