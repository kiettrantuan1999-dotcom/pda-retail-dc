import os
from datetime import datetime, timezone

# APP_VERSION can be set from Railway/GitHub deploy variables.
# If it is not set, each server start gets a new timestamp version.
APP_VERSION = os.getenv("APP_VERSION") or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
