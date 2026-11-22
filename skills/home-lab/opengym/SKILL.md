---
name: opengym
description: Show, change, add or delete Greg's gym routines in openGym, the workout app on his phone, so a change reaches the app on its next sync. Use whenever Greg talks about openGym, his gym routine or workout days (Day A, Day B, Stretch), or wants an exercise swapped, added or removed.
license: MIT
---

# openGym

One command, already on `PATH`. Run it in your shell (the `terminal` tool in
Hermes, Bash in Claude Code, `bash` in pi) exactly as shown: no `python3` in
front and no directory.

```bash
opengym.py show                   # every routine and its exercises, as the app has them
opengym.py show "Day B"           # one routine, with each exercise's note
opengym.py search leg press       # library ids for an exercise name
opengym.py push "Day B"           # make the app's Day B match the plan file
opengym.py push                   # every routine in the plan file
opengym.py delete "Day C"         # remove a routine, by name or id
```

## Changing a routine

1. `opengym.py show` first: Greg may have changed things in the app since.
2. Edit the plan file, `~/Git/home-lab/opengym/gym-routine.opengym.json`. It is
   the only copy outside the app; `~/Git/home-lab/docs/opengym.md` explains its
   format. Take exercise ids from `opengym.py search`; an exercise the library
   lacks goes in the file's `customEx` with a `gh-` id.
3. `opengym.py push "<routine>"`, then commit the plan file in home-lab.

`push` replaces a routine of the same name in place and adds one that is
missing; routines the file does not name are left alone. Never import a plan
file in the app to change a routine: an import always adds a copy.

## Errors

- **No token, or token rejected:** Greg opens `https://gym.grehg2.xyz` in a
  browser, Settings → Account → Pair the mobile app, and gives you the code.
  Run `opengym.py pair <CODE>` within 5 minutes.
- **Cannot reach the server:** the machine needs Tailscale.
- **moria and dungeon each hold a token** (`~/.config/opengym/token`), and each
  stays alive only while used there. With moria asleep, run
  `ssh dungeon 'zsh -lc "opengym.py show"'`, after `git pull` in both repos there.
- **Two routines of one name:** ask Greg which to keep, then `delete` the
  other by the id `show` prints.

Do not edit openGym's files on dungeon or call its API with `curl`: this
command is the way in.
