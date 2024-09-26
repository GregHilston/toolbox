# NixOS

## Shell

We have a preconfigured shell available, with all the required tooling. Simply run `$ nix-shell` and you have everything set up. THis is powered by our `shell.nix` file.

## Just

I use [just](https://github.com/casey/just) to help make commands more easily runnable. To install it, see [this documentation](https://github.com/casey/just?tab=readme-ov-file#packages).

## How To Deploy

TODO update once we have finished our `justfile`

1. On development machine `$ cd nixos`
2. On development machine: `$ scp -r * ghilston@192.168.1.99:/home/ghilston/Git/toolbox/nixos/` or `$ scp -r * nixos:/home/ghilston/Git/toolbox/nixos/`
3. On NixOS Server: `# cp -r ~/Git/toolbox/nixos/* /etc/nixos/`
4. `# nixos-rebuild switch`

## References

- [Hashicorp's Co-Founder Micthell Hashimoto's repo that inspired me to look into development in a VM, using Nix OS](https://github.com/mitchellh/nixos-config?tab=readme-ov-file#how-i-work)
- [Great general purpose Nix Config for macOS with a great README.md](https://github.com/dustinlyons/nixos-config?tab=readme-ov-file#nixos-components). I learned about it from [this Reddit post](https://www.reddit.com/r/Nix/comments/1cv1vq8/why_would_someone_install_nix_on_a_mac_os/l4mus6n/), which how he uses it and why its a benefit.
- [Module, and repository organization reference](https://github.com/Fryuni/config-files)
- home-manager references
  - [tutorial](http://ghedam.at/24353/tutorial-getting-started-with-home-manager-for-nix)
  - [example home.nix](https://github.com/bobvanderlinden/nix-home/blob/master/home.nix)

## TODO

- [ ] Make a configuration.nix file for just isengard in the machines directory and import what i need from our modules. IE dont have gaming be a module that's imported. Make one for nixos vm too and say work machine, etc
- [ ] Add SSH keys to our NixOS to allow us to SSH into the machine
- [ ] Fix nvim config issue with respect to init.lua and init.vim. Open any file with nvim to see the full error message.
- [ ] Get VS Code remote to work with this Nix OS installation. Currently, our remote server fails to be set up.
- [ ] Leverage [nixos-hardware](https://github.com/NixOS/nixos-hardware) for our Lenovo Thinkpad T420, and Lenovo Thinkpad x201.
