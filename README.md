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

## Known Issues

I've had to run `$ make install`, followed by `$ make instal_zsh_autocomplete` manually to get everything installed correctly, then add the word function to the `man` on  ~/.oh-my-zsh/plugins/colored-man-pages/colored-man-pages.plugin.zsh

Running `$ make install` twice can cause `~/.vim` symbolic link incorrectly and cause errors when launching vim. Not sure why yet. Can resolve this by running `$ rm -rf ~/.vim`

### `Unknown function: plug#begin`

Install vim plug, can use `$ make install_vim_plug`

## Notes

### To figure out

- Where to put the following script to disable auto folding
    - command 
    - from https://github.com/plasticboy/vim-markdown#set-header-folding-level

### Vim

- use `:source ~/.config/nvim/init.vim` to resource inside of neovim
- use: gt to switch active tab
- use :f to get the current file's path
- use following to open new tab 
    - :tabnew path/to/file
- use following to move tab 
    - :tabm i
- switch windows, CTRL + W CTRL + W
- horizontal splitting Ctrl+W, S (upper case)
- vertical splitting Ctrl+W, v (lower case) 
- Edit start of line Shift + i
- Edit end of line A
- To switch focus from one window to another, use Ctrl+w <direction> , where direction can be an arrow key or one of the h j k l characters
- Resizing windows 
    - Ctrl+W +/-: increase/decrease height (ex. 20<C-w>+)
    - Ctrl+W >/<: increase/decrease width (ex. 30<C-w><)
    - Ctrl+W _: set height (ex. 50<C-w>_)
    - Ctrl+W |: set width (ex. 50<C-w>|)
    - Ctrl+W =: equalize width and height of all windows
- To indent multiple line Press "<SHIFT> + v" to enter VISUAL LINE mode. Select the text you wish to indent but using either the cursor keys or the "j" and "k" keys. To indent press "<SHIFT> + dot" (> character).

#### Fzf + Ripgrep

- hotkeyed ; to use fzf
    - From inside the menu, fzf will automatically detect ctrl-t to open the file in a new tab, ctrl-v for a vertical split or ctrl-x for a horizontal split.
- to open tabs 
    - From inside the menu, fzf will automatically detect ctrl-t to open the file in a new tab, ctrl-v for a vertical split or ctrl-x for a horizontal split.
    - From the terminal, you can do vim -p filename1 filename2 to open the two files in tabs.
- basically use fzf, hotkeyed to ;, to search for file names
- use rp, :Rg, to search contents of files

#### NerdTree

- Open/Close Nerdtree with :NerdTree and :NerdTreeClose respectively
- Have a hotkey set for CTRL + o

#### tmux 

- To reload confiuguration This can be done either from within tmux, by pressing Ctrl+B and then : to bring up a command prompt, and typing:
  - :source-file ~/.tmux.conf
  - Or simply from a shell:
  - $ tmux source-file ~/.tmux.conf
- to move windows use the hotkey we added to our tmux.conf
    - ctrl + shift + left to move to the left
    - ctrl + shift + right to move to the right
- to toggle fullscreen on a pane ctrl + b + z

#### plasticboy/vim-markdown

- Use : commands to open and close folds
- Otherwise use these
    - zr: reduces fold level throughout the buffer
    - zR: opens all folds
    - zm: increases fold level throughout the buffer
    - zM: folds everything all the way
    - za: open a fold your cursor is on
    - zA: open a fold your cursor is on recursively
    - zc: close a fold your cursor is on
    - zC: close a fold your cursor is on recursively
