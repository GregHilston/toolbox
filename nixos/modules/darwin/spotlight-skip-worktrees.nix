# Keep Spotlight out of git worktrees.
#
# On 2026-11-22 moria's load hit 48, with mds_stores and fseventsd at 150% and
# 120% CPU, indexing hundreds of ~430 MB loser-picks worktrees. A worktree
# cannot take a `.noindex` suffix, and `.metadata_never_index` is not
# honoured below a volume root, so the paths go in the Privacy exclusion list.
# A root daemon refreshes it so new worktrees are covered within minutes.
#
# The daemon needs Full Disk Access (/usr/bin/python3's host, or the nix
# python) to write under .Spotlight-V100; without it the log says so.
{
  pkgs,
  vars,
  ...
}: {
  launchd.daemons.spotlight-skip-worktrees = {
    serviceConfig = {
      ProgramArguments = [
        "${pkgs.python3}/bin/python3"
        "/Users/${vars.user.name}/Git/toolbox/bin/spotlight-exclude-worktrees.py"
        "/Users/${vars.user.name}"
      ];
      RunAtLoad = true;
      StartInterval = 300;
      StandardOutPath = "/var/log/spotlight-skip-worktrees.log";
      StandardErrorPath = "/var/log/spotlight-skip-worktrees.log";
    };
  };
}
