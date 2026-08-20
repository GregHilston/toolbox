# pi-web

PI WEB configuration, deployed to `~/.config/pi-web/config.json`.

**Do not stow this.** `nixos/modules/darwin/pi-web.nix` symlinks it directly
during activation, and `dot/justfile` lists it among the packages the `*-all`
recipes must skip. Stowing it as well makes the two fight over the same path:
stow lays a relative symlink, the next activation replaces it with an absolute
one, and the next `stow`/`restow` fails with "existing target is not owned by
stow".

See `CLAUDE.md` for why the file is a writable symlink rather than a nix-store
one, and why it binds to a tailnet address.
