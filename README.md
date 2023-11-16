# Toolbox
========

My toolbox contains a series of configuration files, helper scripts, and automations to allow me to quickly configure a OSX or Linux environment.

## What's in it?

```bash
├── bin/                                    # Helper scripts. Should be added to $PATH for user convenience.
└── docker/                                 # Contains all scripts related to using Docker to easily test out this toolbox in a throwaway environment.
├── dot/                                    # Dotfiles to configure a slew of programs and environments.
└── secret/                                 # Secrets, such as passwords. Purposefully ignored by Git, and populated on each individual machine.
├── install.sh                              # Single script to leverage this Toolbox to configure an environment just the way I like it.
├── README.md                               # This documentation.
```

## External submodules

Here's a list of third party gitmodules that are included in this repo:
- [oh-my-zsh](https://github.com/robbyrussell/oh-my-zsh)    # zsh customization

## How do I use it?

First, you probably want to fork this repo, change some stuff if you don't like what you see. Then, it's as easy as:

```
./install.sh
```

If you're on a barebones system, like alpine linux, use `$ ./bin/bare_bones.sh` to prepare your system for the `$ ./install.sh` command

And that's it!

## Safely Testing

To safely test the `install.sh` script, I suggest running it in a barebones Debian Docker container. In this repo you'll find the `docker/` directory which is our barebones container and scripts to assist with this. See `docker/README.md` for further instructions.

## Submodules

We use oh-my-zsh as a submodule. This writes to .gitmodules and pulls the code to dot/oh-my-zsh.

### Fixing `Unknown function: plug#begin`

Install vim plug, can use `./bin/install_vim_plug.sh`

## Install Preference

Since Linux has many different ways to install something (from your package manager, snap, flatpak, brew, compile from source, etc...) I've elected to ouse a very specific process. I will not be using Snap or Brew on Linux. While the former has lack of sandboxing that flatpak has, and the latter can conflict build tools with the base linux install, while this generally doesn't cause a problem on OS X. My preference for installation will be:

- apt (via default packages or an external PPA)
- flatpak (via flathub)
- a raw binary
- clone and build

For raw binaries, we'll store them in `~/Apps` and symlink that to `~/bin`

## References:

1. https://www.lorenzobettini.it/2023/07/my-ansible-role-for-oh-my-zsh-and-other-cli-programs/

## TODO

### Ansible Refactor

1. Move dot files from this repository to their respective locations on the target machine
2. install docker and add user to docker group
3. install vim plug, and plugins for vim, and nvim
4. [ ] Test that we're actually installing flatpaks with `./ansible/playbooks/install-flatpaks.yml`, on a VM that has a non-root account, instead of our throwaway Docker container
5. [ ] Look into using [Molecule](https://ansible.readthedocs.io/projects/molecule/), instead of our adhoc throwaway Docker container
6. [ ] Write a playbook to automate, or at least semi automate installing fonts. See [here](https://www.lorenzobettini.it/2023/07/my-ansible-role-for-oh-my-zsh-and-other-cli-programs/)

### Legacy

- Get our i2 dot file to be close to our i3 gaps dot file
- i2-gaps currently does not have a PPA released for Ubuntu 22.04 Jamming Jelly Fish. Once it does, resolve these two issues
    - get i2-gaps to be installed and not just i3-wm. the repository is not working for pop os 22.04
    - Get `dot/i2-gaps/build-i3-config.sh` to be ran, and `/home/ghilston/.i3` directory to be created so we can symlink the build `dot/i3-gaps/config` directory