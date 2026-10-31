# Secrets: 1Password setup and rotation

The rules (everything in vault Infra, `just secrets` from `nixos/`, never commit plaintext)
are in the root `CLAUDE.md` -> "Secret Management".

`just secrets` generates `dot/omlx` settings.json, `dot/pi` models.json and `secrets/.env`.

## Desktop integration, per machine

`op` needs the 1Password desktop integration enabled (Settings -> Developer -> "Integrate
with 1Password CLI").

**macOS 27 blocks it anyway.** `op` then says "No accounts configured", even with the
integration on, because the terminal may not read 1Password's shared data. Fix: System
Settings -> Privacy & Security -> Files & Folders -> your terminal (Ghostty) -> turn on
"Data shared by 1Password", then ⌘Q and reopen the terminal. Never answer `Y` to
`op`'s "add an account manually": that is a separate password login, not this fix. To turn
it on, click the small `>` beside Ghostty; the row itself does nothing. `authorization timeout`
means 1Password wants a prompt approved, so it stalls while Greg is away from the Mac.

## Service account token (moria and dungeon)

moria and dungeon use a service account token instead, so `op` works with nobody at the
Mac. It reads vault Infra and can't write. It lives at `~/.config/op/service-account-token`,
mode `600`, and `just secrets` in both repos picks it up. Keep it in that file, not the
environment, because everything an agent starts inherits its environment. For a one-off read:
`OP_SERVICE_ACCOUNT_TOKEN=$(cat ~/.config/op/service-account-token) op read ...`

Any process running as Greg can read that file, and so all of Infra. pi's file tools deny the
path; pi's bash isn't path-checked.

## Rotating or changing access

Make a new service account (my.1password.com -> Developer -> Directory -> Other; access
can't be edited later), copy the token, then on moria:

```bash
umask 077; pbpaste | tr -d '[:space:]' > ~/.config/op/service-account-token; pbcopy < /dev/null
ssh dungeon 'umask 077; cat > ~/.config/op/service-account-token' < ~/.config/op/service-account-token
```

Then delete the old account. The personal plan allows 1,000 requests a day
([limits](https://www.1password.dev/service-accounts/rate-limits/)); home-lab's `just secrets`
resolves about 133 references.
