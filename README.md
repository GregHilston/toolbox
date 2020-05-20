# Toolbox
========

Inspired by and copied from [davidharrigan](https://github.com/davidharrigan/toolbox) and [msoucy](https://github.com/msoucy/Dotfiles)

My toolbox that allows me to be productive on any system... except Windows.

## What's in it?

```bash
├── Makefile        # Makefile for installation
├── bare_bones.sh   # for preparing a system that has nothing but apt (think alpine linux)
├── bin             # Nifty bin files. Added to $PATH.
├── dots            # Dotfiles
│   ├── bashrc      # BASH config
│   ├── env         # I separate my env vars here - work, OS X specifics
│   ├── gitignore   # Global git ignore
│   ├── oh-my-zsh   # oh-my-zsh installation
│   ├── tmux.conf   # tmux config
│   ├── vimrc       # vim config
│   ├── zsh-custom  # zsh custom theme
│   └── zshrc       # zsh config
├── install     # Installation helper scripts
├── lib         # Nifty libs, iterm2, terminator, terminal colors
│   ├── iterm2
│   ├── terminator
│   └── xrdb
└── private     # My secret sauce.
```

## External submodules

Here's a list of third party gitmodules that are included in this repo:
* [oh-my-zsh](https://github.com/robbyrussell/oh-my-zsh)    # zsh customization


## How do I use it?

First, you probably want to fork this repo, change some stuff if you don't like what you see. Then, it's as easy as:
```
make install
```

If you're on a barebones system, like alpine linux, use `$ ./bare_bones.sh` to prepare your system for the `$ make install` command

And that's it!

## Optional Installs

There are a series of optional installs that can be performed using the `Makefile`.
- docker
- jupter
- samba

## Safely Testing

To safely test the `Makefile`, I suggest running it in a barebones Debian Docker container. In this repo you'll find a `Dockerfile` which is our barebones container.

### To Build Image From `Dockerfile` and Name It

`$ docker build -t linux-test-bed .`

### To Instantiate A Container, For The First Time, By Image Name For Development

`$ docker run -d --name barebones -v $(pwd):/toolbox linux-test-bed`

### To Instantiate A Container, For The First Time, By Image Name For Clean Runs

`$ docker run -d --name barebones linux-test-bed`

### To Run A

`$ docker start barebones`

### To SSH Into Running Container

`$ docker exec -it barebones /bin/bash`

### To SSH Into A Stopped Container

Useful if container is instantly dying, the `--rm` flag removes the container afterwords

`$ docker run --rm -it <image> /bin/bash`

Remember, your `Dockerfile` run command will not execute!

## Known Issues

I've had to run `$ make install`, followed by `$ make instal_zsh_autocomplete` manually to get everything installed correctly, then add the word function to the `man` on  ~/.oh-my-zsh/plugins/colored-man-pages/colored-man-pages.plugin.zsh
