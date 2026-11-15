"""Constants for Jobs AI Switch."""

DOMAIN = "jobs_ai"

# The crew address reaches the Jobs server without Cloudflare Access; the secret guards the switch.
DEFAULT_URL = "https://crew.dwsct.com"

CONF_URL = "url"
CONF_SECRET = "secret"
CONF_NOTIFY = "notify_service"

# How long AI stays on from one approval. The Jobs server never allows more than 15.
ON_MINUTES = 15

# The phone notification's buttons (the entry id is added, so two setups never mix).
ACTION_APPROVE = "JOBS_AI_APPROVE"
ACTION_DENY = "JOBS_AI_DENY"
