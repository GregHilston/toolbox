# Household ledger tools. The ledger itself and its Python environment
# (beancount, fava) live in the private home-lab repo's finance/ and come
# from its uv project; this adds what uv cannot install.
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
