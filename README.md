# Toolbox

---

My toolbox contains a series of configuration files, helper scripts, and automations to allow me to quickly configure an OSX or Linux environment.

## What's In This Repo?

```bash
├── ansible/                                # Ansible playbooks for automation.
├── bin/                                    # Helper scripts. Should be added to $PATH for user convenience.
└── docker/                                 # Contains all scripts related to using Docker to easily test out this toolbox in a throwaway environment.
├── docs/                                   # Additional documentation that supplements this `README.md`
├── dot/                                    # Dotfiles to configure a slew of programs and environments.
└── secret/                                 # Secrets, such as passwords. Purposefully ignored by Git, and populated on each individual machine.
├── bootstrap.sh                            # Optional precursor to install.sh for barebones systems, which prepares an environment for install.sh to be ran.
├── Brewfile                                # Describes which programs to install with Brew.
├── install.sh                              # Main entrypoint to leverage this Toolbox to configure an environment just the way I like it.
├── README.md                               # This documentation.
```

## How Do I Use This Repo?

First, you probably want to fork this repo, change some stuff if you don't like what you see. Then, it's as easy as:

```bash
./install.sh
```

If you're on a barebones system, like alpine linux, use `$ ./bin/bare_bones.sh` fire, to prepare your system for the `$ ./install.sh` command

And that's it!

### How To Run In An Ephemeral Environment

To run this toolbox in an ephemeral environment, I suggest running it in a barebones Ubuntu Docker container. In this repo you'll find the `docker/` directory which is a barebones container and scripts to assist with this. See `docker/README.md` for further instructions.

## My Application Installation Preferences

### OSX

Generally, I'll install everything using Brew.

### Linux

Since Linux has many different ways to install something, from your package manager, snap, flatpak, brew, compile from source, etc...,  I've decided on these preferences for installing software:

1. Via the default package manager. For Debian based distributions this would be `apt`.
2. Flatpak (via flathub).
3. A raw binary. Which we'll store in `~/Apps` and symlink them to `~/bin`.
4. clone and build

I've decided against using Snap, due to its widespread criticism.

## References

1. https://www.lorenzobettini.it/2023/07/my-ansible-role-for-oh-my-zsh-and-other-cli-programs/

## TODO

### Ansible Refactor

1. [ ] Make everything into variables, so other users can this repo
2. [ ] Make the `install.sh` script take in an environment name, which can be used to call different ansible playbooks.
3. [ ] Clean up our `./bin` directory, removing all old scripts, and ensuring that the scripts are both bash files, in our path, and accessible to our `~/.zshrc`? or perhaps just being in the path is enough for autocomplete.
4. [ ] Remove all legacy dot files. see the `./dot/` directory for old files, and `./dot/README.md`'s mentions of the word "legacy" to determine what to remove
5. [ ] Discuss if `bootstrap.sh` should still use [bash strict mode](http://redsymbol.net/articles/unofficial-bash-strict-mode/). Recall that Jesse's Proxmox VM's `$ apt-get update` failed, and exited
6. [ ] Look into using [Molecule](https://ansible.readthedocs.io/projects/molecule/), instead of our adhoc throwaway Docker container
7. [ ] Write a playbook to automate, or at least semi automate installing fonts. See [here](https://www.lorenzobettini.it/2023/07/my-ansible-role-for-oh-my-zsh-and-other-cli-programs/)

### Legacy

- Get our i3 dot file to be close to our i3 gaps dot file
- i3-gaps currently does not have a PPA released for Ubuntu 22.04 Jamming Jelly Fish. Once it does, resolve these two issues
  - get i3-gaps to be installed and not just i3-wm. the repository is not working for pop os 22.04
  - Get `dot/i3-gaps/build-i3-config.sh` to be ran, and `/home/ghilston/.i3` directory to be created so we can symlink the build `dot/i3-gaps/config` directory
