# NixOS

## Pre Configured Shell

We have a pre configured shell available, with all the required tooling. Simply run `$ nix-shell` and you have everything set up. This is powered by our `shell.nix` file, and is useful on a freshly installed NixOS machine.

## Useful Commands

I use [just](https://github.com/casey/just), a tool similar to Make, to help make commands more easily runnable. To install it, see [this documentation](https://github.com/casey/just?tab=readme-ov-file#packages). This is all powered by our `justfile`.

## How To Build/Deploy

`$ just deploy [machine name]`

See `flake.nix` for machine names, these are based off of `hosts/`.

## NixOS Pattern

1. Our usage of Just will leverage a `--flake` argument, passed by the CLI as an argument, indicating what machine we'll be building and deploying by pointing to a specific section in `flake.nix`.
2. Configuration variables are defined n `config/vars.nix`. These can be overridden by each `./hosts/`'s `default.nix`. This is done here, as we're using `flake.nix` for system level configurations.
3. The machine's `flake.nix` section will point to a `./hosts/[machine-name]`, which will resolve to `./hosts/[machine-name]/default.nix`.
4. That `./hosts/[machine-name]/default.nix` file will define system things, and point to that machine's `./hosts/[machine-name]/hardware-configuration.nix`, and any and all `./modules/` that are relevant for that machine. For example, like `./modules/home/default.nix` which defines user packages.

## To View Your NixOs Version

`$ nixos-version`

## How To Update To New Version

1. In your flake.nix, you need to update the following inputs:

```nix
nixpkgs.url = "github:nixos/nixpkgs/nixos-24.11";
home-manager = {
  url = "github:nix-community/home-manager/release-24.11";
  inputs.nixpkgs.follows = "nixpkgs";
};
stylix.url = "github:danth/stylix/release-24.11";
```
2. Update your flake.lock file: `$ nix flake update`. This command can take a while.
3. Then rebuild your system: `$ just deploy <host-name>`

## References

- [krisztian fekete write's some NixOS tips and organization of your repo](https://krisztianfekete.org/nine-months-of-nixos/)
- [Hashicorp's Co-Founder Micthell Hashimoto's repo that inspired me to look into development in a VM, using Nix OS](https://github.com/mitchellh/nixos-config?tab=readme-ov-file#how-i-work)
- [Great general purpose Nix Config for macOS with a great README.md](https://github.com/dustinlyons/nixos-config?tab=readme-ov-file#nixos-components). I learned about it from [this Reddit post](https://www.reddit.com/r/Nix/comments/1cv1vq8/why_would_someone_install_nix_on_a_mac_os/l4mus6n/), which how he uses it and why its a benefit.
- [Module, and repository organization reference](https://github.com/Fryuni/config-files)
- home-manager references
  - [tutorial](http://ghedam.at/24353/tutorial-getting-started-with-home-manager-for-nix)
  - [example home.nix](https://github.com/bobvanderlinden/nix-home/blob/master/home.nix)
- [example of separating out per program configuration](https://github.com/hans-chrstn/.dotfiles/tree/main/home/common/programs)
  - [another example, which separates out gui and tui configs](https://github.com/GaetanLepage/nix-config/tree/master/home/modules)
  - [and another](https://github.com/AlexNabokikh/nix-config/tree/master/files/configs/nvim)
- Useful font tools
  - [Nerd Fords visualizer and explorer](https://www.nerdfonts.com/)
  - [compare two fonts](https://www.pairandcompare.net/)
- [Ricing guide with Stylix](https://journix.dev/posts/ricing-linux-has-never-been-easier-nixos-and-stylix/)
- [Great wallpapers](https://github.com/dharmx/walls/tree/main)

## TODO

- [ ] Add other window managers, like i3 and i3 + KDE
- [ ] Get nvim copy to clipboard to work. See [here](https://discourse.nixos.org/t/how-to-support-clipboard-for-neovim/9534/3), and [here](https://www.reddit.com/r/neovim/comments/3fricd/easiest_way_to_copy_from_neovim_to_system/)
- [ ] Get VS Code remote to work with this Nix OS installation. Currently, our remote server fails to be set up.
