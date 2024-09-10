# NixOS

## Just

I use [just](https://github.com/casey/just) to help make commands more easily runnable. To install it, see [this documentation](https://github.com/casey/just?tab=readme-ov-file#packages).

## How To Deploy

1. On development machine `$ cd nixos`
2. On development machine: `$ scp -r * ghilston@192.168.1.99:/home/ghilston/Git/toolbox/nixos/` or `$ scp -r * nixos:/home/ghilston/Git/toolbox/nixos/`
3. On NixOS Server: `# cp -r ~/Git/toolbox/nixos/* /etc/nixos/`
4. `# nixos-rebuild switch`

## References

- [Module, and repository organization reference](https://github.com/Fryuni/config-files)
- home-manager references
  - [tutorial](http://ghedam.at/24353/tutorial-getting-started-with-home-manager-for-nix)
  - [example home.nix](https://github.com/bobvanderlinden/nix-home/blob/master/home.nix)

## TODO

- [ ] Fix nvim config issue with respect to init.lua and init.vim. Open any file with nvim to see the full error message.
- [ ] Get VS Code remote to work with this Nix OS installation. Currently, our remote server fails to be set up.
- [ ] Leverage [nixos-hardware](https://github.com/NixOS/nixos-hardware) for our Lenovo Thinkpad T420, and Lenovo Thinkpad x201.
