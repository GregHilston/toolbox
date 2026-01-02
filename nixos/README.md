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
Smart directory jumping that learns your habits. **Use `z` instead of `cd`!**

```bash
z projects        # Jump to any directory matching "projects"
z nix            # Jump to your most-used directory with "nix" in the path
zi               # Interactive fuzzy selection with fzf

# Still works if you really need it
builtin cd /path  # Traditional cd
```

**Why use `z`?**
- **Learns your habits**: Tracks which directories you visit most
- **Frecency algorithm**: Combines frequency + recency
- **Partial matches**: Type less, get there faster
- **No full paths needed**: `z proj` might jump to `~/work/myproject`

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

### Tmux
Enhanced terminal multiplexer with vim-aware navigation.

**Basic Usage:**
```bash
tmux          # Start new session
tmux ls       # List sessions
tmux attach   # Attach to last session
```

**Key Bindings:** (Prefix is `Ctrl+b` by default)
- **Prefix + |**: Split pane vertically
- **Prefix + -**: Split pane horizontally
- **Prefix + r**: Reload tmux config
- **Ctrl+h/j/k/l**: Navigate between panes (works with vim!)
- **Shift+Arrow**: Resize current pane

**Features:**
- Vi mode in copy mode (Prefix + [ to enter)
- Mouse support (scroll, select panes, resize)
- 10,000 line scrollback history
- True color support (256+ colors)
- Seamless vim/tmux navigation

**Note about VS Code:** VS Code's command suggestions UI (the autocomplete with star/favorite button) **does not work inside tmux**. This is a VS Code GUI feature that requires direct terminal control. When tmux runs, VS Code can't overlay its suggestion UI on tmux panes.

**Recommendation:** Use VS Code's integrated terminal (without tmux) for interactive work to get all autocomplete features. Use tmux only when you need:
- Persistent sessions that survive SSH disconnects
- Shared terminal sessions
- Long-running background processes

## Per-Project Development Environments

We use `direnv` + Nix flakes for automatic, isolated development environments.

### How It Works

When you enter a project directory with a `flake.nix` and `.envrc`, direnv automatically loads the project's tools (Python, Node.js, Go, etc.). When you leave, it unloads them.

### Setup a New Project

#### Python Project
```bash
# Create project
mkdir my-python-project && cd my-python-project

# Create flake.nix
cat > flake.nix << 'EOF'
{
  inputs.nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  outputs = { nixpkgs, ... }: {
    devShells.aarch64-linux.default = nixpkgs.legacyPackages.aarch64-linux.mkShell {
      packages = with nixpkgs.legacyPackages.aarch64-linux; [
        python312
        python312Packages.pip
      ];
    };
  };
}
EOF

# Enable direnv
echo "use flake" > .envrc
direnv allow

# Python is now available!
python --version
```

#### TypeScript/JavaScript Project
```bash
mkdir my-ts-project && cd my-ts-project

# Create flake.nix
cat > flake.nix << 'EOF'
{
  inputs.nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  outputs = { nixpkgs, ... }: {
    devShells.aarch64-linux.default = nixpkgs.legacyPackages.aarch64-linux.mkShell {
      packages = with nixpkgs.legacyPackages.aarch64-linux; [
        nodejs_22
        yarn
      ];
    };
  };
}
EOF

echo "use flake" > .envrc
direnv allow

# Node.js is now available!
node --version
```

**Note:** Change `aarch64-linux` to `x86_64-linux` if not on ARM.

**Benefits:**
- No global package installation
- Each project has isolated dependencies
- Auto-loads when you `cd` into the project
- Works with VS Code (install `mkhl.direnv` extension)

## Useful Commands

I use [just](https://github.com/casey/just), a tool similar to Make, to help make commands more easily runnable. To install it, see [this documentation](https://github.com/casey/just?tab=readme-ov-file#packages). This is all powered by our `justfile`.

## How To Build/Deploy

`$ just deploy [machine name]`

See `flake.nix` for machine names, these are based off of `hosts/`.

## NixOS in WSL (Windows Subsystem for Linux)

### Initial Setup (Foundation)

If you need to install NixOS WSL from scratch:

1. **Download NixOS WSL** (in PowerShell):
   ```powershell
   Invoke-WebRequest -Uri https://github.com/nix-community/NixOS-WSL/releases/download/2405.5.4/nixos-wsl.tar.gz -OutFile nixos-wsl.tar.gz
   ```

2. **Import into WSL**:
   ```powershell
   wsl --import NixOS $env:USERPROFILE\NixOS nixos-wsl.tar.gz
   wsl --set-default NixOS
   ```

3. **Start WSL and deploy configuration**:
   ```powershell
   wsl -d NixOS
   ```

   Once inside (you'll be the `nixos` user):
   ```bash
   # Install git temporarily (not in base install)
   nix-shell -p git

   # Clone your config
   git clone https://github.com/GregHilston/toolbox ~/Git/toolbox
   cd ~/Git/toolbox/nixos

   # Deploy the foundation configuration
   # This will create your ghilston user and set everything up
   sudo nixos-rebuild switch --flake .#foundation

   # Exit both nix-shell and WSL
   exit
   exit
   ```

4. **Restart WSL** (in PowerShell):
   ```powershell
   wsl --shutdown
   wsl
   ```

   You should now be logged in as `ghilston` user with your full configuration!

### VS Code Remote-WSL Setup

**Option 1: Remote-WSL Extension (Recommended)**
- Install the [Remote-WSL](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-wsl) extension in VS Code on Windows
- Click the remote indicator in bottom-left corner → "Connect to WSL"
- VS Code automatically connects using native WSL integration
- **No SSH needed** - Microsoft's native approach

**Option 2: Remote-SSH Extension**
- Would require SSH service configuration (not currently enabled on foundation)
- Less common for WSL, but possible if needed

### Troubleshooting: Nuclear Option (Complete Reinstall)

If your WSL instance is broken and you need to start completely fresh:

**⚠️ WARNING: This will delete ALL data in your WSL instance!**

1. **Backup important data** (in PowerShell):
   ```powershell
   # Check what's in your home directory first
   ls \\wsl$\NixOS\home\ghilston\

   # Copy anything important to Windows
   Copy-Item -Recurse \\wsl$\NixOS\home\ghilston\important-folder C:\Backup\
   ```

2. **Unregister the broken WSL instance**:
   ```powershell
   # Check current WSL distributions
   wsl --list --verbose

   # Unregister NixOS (this deletes everything!)
   wsl --unregister NixOS
   ```

3. **Follow the Initial Setup steps above** to reinstall from scratch

## NixOS in a VM

### VM Filesystem Sharing

This project uses bidirectional filesystem sharing between macOS host and NixOS VMs for development.

#### macOS Host → NixOS VM (Access Mac files from VM)

**Method:** virtiofs (VMware shared folders)
**Mount Point:** `/host` in NixOS VM
**Source:** macOS home directory

VMware Fusion automatically shares the macOS filesystem with the VM using virtiofs. NixOS mounts it at `/host`.

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
- High performance (kernel-level filesystem)
- Changes visible immediately on both macOS and VM
- Configured in [hosts/vms/mines/default.nix:24-35](hosts/vms/mines/default.nix#L24-L35)

#### NixOS VM → macOS Host (Access VM files from Mac)

**Method:** NFS (Network File System)
**Mount Point:** `/System/Volumes/Data/vm/mines` on macOS (symlinked to `~/mines` for convenience)
**Source:** `/home/ghilston` in NixOS VM

**Setup:**

1. Ensure NFS server is configured in NixOS VM (already configured in [hosts/vms/mines/default.nix:83-88](hosts/vms/mines/default.nix#L83-L88)):
   ```nix
   services.nfs.server = {
     enable = true;
     exports = ''
       /home/ghilston *(rw,sync,no_subtree_check,all_squash,anonuid=1000,anongid=1000,insecure)
     '';
   };
   ```
   Note: The `insecure` option is required for macOS NFS clients.

2. Deploy the NixOS configuration:
   ```bash
   just fr mines
   ```

3. Run the setup script on macOS (one-time setup):
   ```bash
   ./scripts/setup-nfs-mount.sh
   ```

4. **Reboot your Mac** (required once for `/vm` to be created via synthetic.conf)

5. Run the setup script again after reboot to complete NFS configuration

**Usage:**
- Access VM files at `~/mines` (convenient symlink)
- Or use full path: `/System/Volumes/Data/vm/mines`
- Auto-mounts on first access (e.g., `ls ~/mines`)
- Auto-unmounts when idle
- Survives reboots of both host and guest
- Works in all macOS apps (Finder, VSCode, Bruno, etc.)

**Note:** If VM IP changes, re-run `./scripts/setup-nfs-mount.sh` to update the configuration. For zero-maintenance operation, configure a static IP for your VM.

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

### VS Code Remote-SSH Setup

VS Code runs on macOS as a client and connects to the NixOS VM via SSH. The VS Code GUI runs on the host while VS Code Server runs automatically in the VM.

**Setup:**

1. Add your SSH public key (`~/.ssh/id_rsa.pub`) to [modules/common/default.nix](modules/common/default.nix#L102-L104):
   ```nix
   users.users.${vars.user.name} = {
     openssh.authorizedKeys.keys = [
       "ssh-rsa AAAAB3Nza... your-public-key-here"
     ];
   };
   ```

2. Deploy configuration: `just fr mines`

3. Configure `~/.ssh/config` with your VM details:
   ```ssh-config
   Host <vm-name>
       HostName <vm-ip>
       User <username>
       IdentityFile ~/.ssh/id_rsa
       IdentitiesOnly yes
       ForwardAgent yes
   ```

4. Install "Remote - SSH" extension in VS Code on macOS

5. Connect via `Cmd+Shift+P` → "Remote-SSH: Connect to Host"

**Why:** Combines macOS hardware/battery with Linux development environment. VS Code is disabled in the VM config ([hosts/vms/mines/default.nix:128](hosts/vms/mines/default.nix#L128)) since it runs on the macOS host.

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

### Command For Git Repositories

```bash
$ mkdir -p ~/nixos-references
$ cd ~/Git/nixos-references
$ git clone https://github.com/mitchellh/nixos-config.git mitchellh-nixos-config
  git clone https://github.com/dustinlyons/nixos-config.git dustinlyons-nixos-config
  git clone https://github.com/Fryuni/config-files.git fryuni-config-files
  git clone https://github.com/GaetanLepage/nix-config.git gaetanlepage-nix-config
  git clone https://github.com/hans-chrstn/.dotfiles.git hans-chrstn-dotfiles
  git clone https://github.com/AlexNabokikh/nix-config.git alexnabokikh-nix-config
```

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
