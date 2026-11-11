# What the home-lab ledger's uv env can't install.
{
  pkgs,
  vars,
  ...
}: {
  home-manager.users.${vars.user.name}.home.packages = [
    # pdftotext, which the PDF statement parser needs.
    pkgs.poppler-utils
  ];
}
