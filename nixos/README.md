# NixOS

## How To Deploy

1. On development machine `$ cd nixos`
2. On development machine: `$ scp -r * ghilston@192.168.1.99:/home/ghilston/Git/toolbox/nixos/` or `$ scp -r * nixos:/home/ghilston/Git/toolbox/nixos/`
3. On NixOS Server: `# cp -r ~/Git/toolbox/nixos/* /etc/nixos/`
4. `# nixos-rebuild switch`

## TODO

- [ ] Get VS Code remote to work with this Nix OS installation. Currently, our remote server fails to be set up.
- [ ] Leverage [nixos-hardware](https://github.com/NixOS/nixos-hardware) for our Lenovo Thinkpad T420, and Lenovo Thinkpad x201.
