"""Data providers (Google and the simulated demo mode).

Logging safety: the HTTP libraries log every request address at INFO level,
and Google request addresses can contain the API key. Turning those loggers
down here means the key can never reach a log, whichever provider module is
imported first.
"""

import logging

for _name in ("httpx", "httpcore", "hpack"):
    logging.getLogger(_name).setLevel(logging.WARNING)
