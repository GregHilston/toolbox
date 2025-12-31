# NixOS

## Pre Configured Shell

We have a pre configured shell available, with all the required tooling. Simply run `$ nix-shell` and you have everything set up. This is powered by our `shell.nix` file, and is useful on a freshly installed NixOS machine.

## Modern Shell Tools

Our configuration includes modern CLI tools for better productivity:

### Starship Prompt
A fast, customizable shell prompt showing git status, nix-shell context, and directory info.
- Automatically shows git branch and status
- Indicates when in a nix-shell
- Clean, minimal design

### Zoxide
Smart directory jumping that learns your habits.
```bash
z <partial-path>  # Jump to most frecent matching directory
zi                # Interactive selection with fzf
```

### fzf
Interactive fuzzy finder for files, history, and directories.
- **Ctrl+R**: Search command history
- **Ctrl+T**: Search and insert files/directories
- **Alt+C**: cd into directory

### Eza
Modern `ls` replacement with colors, icons, and git integration.
```bash
ls      # List files with icons and colors
ll      # Long listing format
la      # Show all files including hidden
lt      # Tree view
lla     # Long listing with all files
```

### Git Aliases
Useful git shortcuts:
```bash
git st        # status
git co        # checkout
git br        # branch
git lg        # pretty graph log
git cleanup   # remove merged branches
```

## Useful Commands

I use [just](https://github.com/casey/just), a tool similar to Make, to help make commands more easily runnable. To install it, see [this documentation](https://github.com/casey/just?tab=readme-ov-file#packages). This is all powered by our `justfile`.

## How To Build/Deploy

`$ just deploy [machine name]`

See `flake.nix` for machine names, these are based off of `hosts/`.

## NixOS in a VM

### Host Filesystem Sharing (Mines VM)

The Mines VM has read-write access to the entire macOS filesystem at `/host`:

**Access macOS files from the VM:**
```bash
# View macOS Downloads
ls /host/ghilston/Downloads

# Edit a file on macOS
nvim /host/ghilston/Documents/myfile.txt

# Work on macOS projects from the VM
cd /host/ghilston/Projects/myproject
```

**Features:**
- Full read-write access with `umask=22` (new files readable by group/others, writable by owner)
- Changes visible immediately on both macOS and VM
- Powered by VMware's vmhgfs-fuse filesystem driver
- Based on Mitchell Hashimoto's configuration pattern

### Boot Drive Space Management

The boot partition (`/boot`) in our NixOS VM is only 512MB. This can fill up quickly with multiple NixOS generations, preventing system rebuilds and updates.

**To check boot space usage:**
```bash
df -h /boot
```

**To free up space:**

Option 1 - Remove old generations (keeps last 7 days):
```bash
sudo nix-collect-garbage --delete-older-than 7d
sudo nixos-rebuild boot
```

Option 2 - Aggressive cleanup (keeps only current generation):
```bash
sudo nix-collect-garbage -d
sudo nixos-rebuild boot
```

**Alternative:** You can expand the boot partition size using GParted from a NixOS live ISO, but the cleanup commands above are simpler and usually sufficient.

### Copy and Paste in VMware Fusion

#### Within the NixOS VM
- **GUI Applications (VS Code, etc.)**: `Ctrl+C` to copy, `Ctrl+V` to paste
- **Alacritty Terminal**: `Ctrl+Shift+C` to copy, `Ctrl+Shift+V` to paste

#### Between macOS Host and NixOS VM

**Mac → NixOS VM:**
- Copy on Mac: `Cmd+C`
- Paste in VM GUI apps: `Ctrl+V`
- Paste in VM terminal: `Ctrl+Shift+V`

**NixOS VM → Mac:**
- Copy in VM GUI apps: `Ctrl+C`
- Copy in VM terminal: `Ctrl+Shift+C` (requires `wl-clipboard` package)
- Paste on Mac: `Cmd+V`

**Prerequisites:**
- VMware Tools must be installed (included in this configuration)
- `wl-clipboard` package required for Wayland clipboard sync (included in this configuration)
- VMware Fusion clipboard sharing must be enabled in VM settings

**Troubleshooting:**
- If terminal copy doesn't sync to Mac, ensure text is properly selected before copying
- Restart VM if clipboard sync stops working
- Check VMware Fusion VM Settings → Sharing → Enable clipboard sharing

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
2. Make sure that your `flake.nix`'s configuration for the target machine has a URL that looks like `nixpkgs-unstable.lib.nixosSystem`
// 3. Update your flake.lock file: `$ nix flake update`. This command can take a while.
4. Then rebuild your system: `$ just upgrade <host-name>`

## References

### NixOS VM Development

- https://github.com/mitchellh/nixos-config
- https://www.youtube.com/watch?v=ubDMLoWz76U
- https://www.joshkasuboski.com/posts/nix-dev-environment/
- https://nix.dev/tutorials/nixos/nixos-configuration-on-vm.html

### General NixOS References

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

- 