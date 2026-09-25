# Generated into ~/.hermes/profiles/<bot>/.env by `just secrets`, once per bot.
#
# A SECONDARY profile does not fall back to the root ~/.hermes/.env, and that is
# deliberate: config.py's `_env_ref_lookup` resolves `${VAR}` through the profile
# secret scope, and `get_secret` returns a miss rather than another profile's
# value (upstream #84079 — every profile "had" the default profile's
# ${MATRIX_ACCESS_TOKEN} and fanned out). An unresolved ref stays VERBATIM, so
# `api_key: ${OMLX_API_KEY}` goes out as the literal string and oMLX answers
# `HTTP 401: Invalid API key`.
#
# The default profile is the exception — it reads plain os.environ — which is
# why the CLI, and Telegram (which routes to `default`), worked for a whole
# session while every Bot Chat 401'd.
#
# The model keys ONLY. Not the Telegram token: these bots have no transport of
# their own, and one file per profile is what keeps #84079's isolation real
# instead of symlinking the root .env into every one of them.
OMLX_API_KEY={{ op://Infra/oMLX/api_key }}
DEEPSEEK_API_KEY={{ op://Infra/DeepSeek/api_key }}
