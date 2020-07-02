import datetime
import pytz


def now():
    return pytz.utc.localize(datetime.datetime.utcnow())
