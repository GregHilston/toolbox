# based on these two references:
# 1. https://github.com/namishh/crystal/blob/main/home/namish/conf/browsers/firefox/default.nix
# 2. https://github.com/gvolpe/nix-config/blob/master/home/programs/firefox/default.nix
{
  config,
  pkgs,
  ...
}: {
  programs.firefox = {
    enable = true;
    profiles = {
      default = {
        id = 0;
        name = "default";
        isDefault = true;
        settings = {
          "browser.startup.homepage" = "https://google.com";

          "toolkit.legacyUserProfileCustomizations.stylesheets" = true;
          "general.smoothScroll" = true;
          "layers.acceleration.force-enabled" = true;
          "media.av1.enabled" = false;
          "media.ffmpeg.vaapi.enabled" = true;
          "media.hardware-video-decoding.force-enabled" = true;
          "media.rdd-ffmpeg.enabled" = true;
          "widget.dmabuf.force-enabled" = true;
          "widget.use-xdg-desktop-portal" = true;
          "extensions.pocket.enabled" = false;
          "extensions.pocket.onSaveRecs" = false;
        };
        search = {
          force = true;
          default = "google";
          order = ["google"];
          engines = {
            "Nix Packages" = {
              urls = [
                {
                  template = "https://search.nixos.org/packages";
                  params = [
                    {
                      name = "type";
                      value = "packages";
                    }
                    {
                      name = "query";
                      value = "{searchTerms}";
                    }
                  ];
                }
              ];
              icon = "''${pkgs.nixos-icons}/share/icons/hicolor/scalable/apps/nix-snowflake.svg";
              definedAliases = ["@np"];
            };
            "bing".metaData.hidden = true;
            "google".metaData.alias = "@g"; # builtin engines only support specifying one additional alias
          };
        };

        # Recall that you have to manually enable these in Firefox on initial install
        # OLD:extensions = with pkgs.nur.repos.rycee.firefox-addons; [
        # NEW:
        extensions.packages = with pkgs.nur.repos.rycee.firefox-addons; [
          bitwarden
          vimium
          unpaywall
          link-cleaner

          # auto-accepts cookies, use only with privacy-badger & ublock-origin
          istilldontcareaboutcookies
          ublock-origin
          privacy-badger
          re-enable-right-click
          don-t-fuck-with-paste

          # enhancer-for-youtube
          sponsorblock
          return-youtube-dislikes

          darkreader
          enhanced-github
          refined-github
          github-file-icons
          reddit-enhancement-suite
        ];
      };
    };
  };
}
