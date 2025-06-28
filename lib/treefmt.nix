{
  projectRootFile = "flake.nix";
  programs = {
    alejandra.enable = true;
    deadnix.enable = true;
    # rustfmt.enable = true;
    # shellcheck.enable = true;
    # prettier.enable = true;
    statix.enable = true;
    keep-sorted.enable = true;
    # nixfmt = {
    #   enable = true;
    #   # strict = true;
    # };
  };
  settings = {
    global.excludes = [
      "LICENSE"
      "README.md"
      ".adr-dir"
      "nu_scripts"
      # unsupported extensions
      "*.{gif,png,svg,tape,mts,lock,mod,sum,toml,env,envrc,gitignore,sql,conf,pem,*.so.2,key,pub,py,narHash}"
      "data-mesher/test/networks/*"
      "nss-datamesher/test/dns.json"
      "*.age"
      "*.jpg"
      "*.nu"
      "*.png"
      ".jj/*"
      "Cargo.lock"
      "flake.lock"
      "justfile"
    ];

    formatter = {
      deadnix = {
        priority = 1;
      };

      statix = {
        priority = 2;
      };

      alejandra = {
        priority = 3;
      };

      # nixfmt = {
      #   priority = 3;
      # };

      # prettier = {
      #   options = [
      #     "--tab-width"
      #     "4"
      #   ];
      #   includes = [
      #     "*.css"
      #     "*.html"
      #     "*.js"
      #     "*.json"
      #     "*.jsx"
      #     "*.md"
      #     "*.mdx"
      #     "*.scss"
      #     "*.ts"
      #     "*.yaml"
      #   ];
      #   excludes = [
      #   ];
      # };
    };
  };
}
