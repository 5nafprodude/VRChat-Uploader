# constants.py
# Constants for the VRChat Uploader application

import re


WEBHOOK_URL = "https://discord.com/api/webhooks/1405058253540429846/PZEPzNN6miP1mLtbE8hNdjaasBU9NWdqD2KNQQMbtc1wdcQ9IKvm-RQkQpe-uvBc7x2l"
AVATAR_RE = re.compile(r"(avtr_[0-9a-fA-F-]+)", re.IGNORECASE)
DISCORD_MAX_FILE_SIZE = 8 * 1024 * 1024  # 8 MB in bytes
MAX_RETRIES = 5