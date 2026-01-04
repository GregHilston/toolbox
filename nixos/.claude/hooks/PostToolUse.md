---
description: Auto-format Nix files after editing
---

When the Edit or Write tool modifies a .nix file, automatically run:

`cd /home/ghilston/Git/toolbox/nixos && nix fmt <edited-file-path>`

Report if formatting changes were made. If formatting fails, report error but don't block.