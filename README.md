# Toolbox
========

Inspired by and copied from [davidharrigan](https://github.com/davidharrigan/toolbox) and [msoucy](https://github.com/msoucy/Dotfiles)

My toolbox that allows me to be productive on any system... except Windows.

## What's in it?

```bash
├── Makefile                                # Makefile for installation
├── bin                                     # Nifty bin files. Added to $PATH.
├── dot                                     # Dotfiles
│   ├── config/nvim/init.vim                # nvim config
│   ├── hammerspoon/init.lua                # hammerspoon config (for mac)
│   ├── i3/config                           # i3 config
│   ├── vim/                                # ? TODO figure out
│   ├── zsh-custom/                         # zsh custom theme
│   ├── tmux.conf                           # tmux config
│   ├── vimrc                               # vim config (Outdated, as we prefer to use config/nvim/init.vim)
│   ├── vs_code_settings_sync_gist_url.txt  # gist for vs code extension settings
│   ├── oh-my-zsh                           # oh-my-zsh installation
│   ├── spectacle_config.png                # spectacle config (for mac)
│   └── zshrc                               # zsh config
├── install                                 # Installation helper scripts
└── secret                                  # My secret sauce
```

## External submodules

Here's a list of third party gitmodules that are included in this repo:
* [oh-my-zsh](https://github.com/robbyrussell/oh-my-zsh)    # zsh customization


## How do I use it?

First, you probably want to fork this repo, change some stuff if you don't like what you see. Then, it's as easy as:
```
make install
```

If you're on a barebones system, like alpine linux, use `$ ./bin/bare_bones.sh` to prepare your system for the `$ make install` command

And that's it!

## Safely Testing

To safely test the `Makefile`, I suggest running it in a barebones Debian Docker container. In this repo you'll find a `Dockerfile` which is our barebones container.

### To Build Image From `Dockerfile` and Name It

`$ docker build -t linux-test-bed .`

### To Instantiate A Container, For The First Time, By Image Name For Development

`$ docker run -d --name barebones -v $(pwd):/toolbox linux-test-bed`

### To Instantiate A Container, For The First Time, By Image Name For Clean Runs

`$ docker run -d --name barebones linux-test-bed`

### To Run A Container

`$ docker start barebones`

### To Shell Exec Into Running Container

`$ docker exec -it barebones /bin/bash`

### To SSH Into A Stopped Container

Useful if container is instantly dying, the `--rm` flag removes the container afterwords

`$ docker run --rm -it <image> /bin/bash`

Remember, your `Dockerfile` run command will not execute!

## Submodules

I hadn't used submodules prior to working with this. We use oh-my-zsh as a submodule. This writes to .gitmodules and pulls the code to dot/oh-my-zsh. As I write this, no idea why this lives in dot.

## Vim

## vim-plug

With efforts to learn more vim, I'm using vim-plug to install plugins. For my own memory, I'll write some plugins and what they do/how to use them to remind myself.

In vim, run the command `:PlugStatus` to check the status of the plugins

#### fzf

I have this mapped to ';', which will fuzzy search

#### nerd tree

Mapped to "ctrl + o"

#### flake 8

Mapped to F7


## Notes

As I start to try to use Vim more and other tools, I find myself learning commands that I want to remember and add to my daily workflow. I'll add these notes to a notes.md file.

## Known Issues

I've had to run `$ make install`, followed by `$ make instal_zsh_autocomplete` manually to get everything installed correctly, then add the word function to the `man` on  ~/.oh-my-zsh/plugins/colored-man-pages/colored-man-pages.plugin.zsh

Running `$ make install` twice can cause `~/.vim` symbolic link incorrectly and cause errors when launching vim. Not sure why yet. Can resolve this by running `$ rm -rf ~/.vim`

### `Unknown function: plug#begin`

Install vim plug, can use `$ make install_vim_plug`
