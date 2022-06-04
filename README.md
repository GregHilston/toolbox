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

To safely test the `install.sh` script, I suggest running it in a barebones Debian Docker container. In this repo you'll find the `docker/` directory which is our barebones container and scripts to assist with this.

## Submodules

I hadn't used submodules prior to working with this. We use oh-my-zsh as a submodule. This writes to .gitmodules and pulls the code to dot/oh-my-zsh.

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

Install vim plug, can use `./bin/install_vim_plug.sh`

## TODO

- get i3-gaps to be installed and not just i3-wm. the repository is not working for pop os 22.04

## References

### Git Plugin Hotkeys

see `~/.oh-my-zsh/plugins/git/git.plugin.zsh`, after installing

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
