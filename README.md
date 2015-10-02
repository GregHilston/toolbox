Toolbox
========
My toolbox that allows me to be productive on any system... except Windows.
Includes dotfiles, handy scripts, cool colors for use on Linux and OSX.

## What's in it?
```bash
├── Makefile     # Makefile for installation
├── Vagrantfile  # Vagrantfiles are just handy to have around, right?
├── backup       # Any existing replaced files will go here
├── bin          # Nifty bin files. Added to $PATH.
├── dots         # Dotfiles
│   ├── bashrc
│   ├── env      # I separate my env vars here - work, OS X specifics
│   ├── gitignore
│   ├── oh-my-zsh
│   ├── tmux.conf
│   ├── vim
│   ├── vimrc
│   ├── zsh
│   └── zshrc
├── install     # Installation helper scripts
├── lib         # Nifty libs, iterm2, terminator, terminal colors
│   ├── iterm2
│   ├── terminator
│   └── xrdb
└── private     # My secret sauce.
```

## External submodules
Here's a list of third party gitmodules that are included in this repo:
* [oh-my-zsh](https://github.com/robbyrussell/oh-my-zsh)
* [Vundle](https://github.com/VundleVim/Vundle.vim)


## How do I use it?
First, you probably want to fork this repo, change some stuff if you don't like what you see. Then, it's as easy as:
```
make install
```

[YouCompleteMe](https://github.com/Valloric/YouCompleteMe) is listed inside `vimrc`, however is not installed by default. I have it configured to install
autocompletion for Python, Javascript, and Go by default. There are some dependencies that need to be taken care of first.

### OS X
1. Make sure you are using the MacVim vim binary:
```
ln -s /usr/local/bin/mvim vim
```
2. Install Node.js
```
brew install node
```
3. Install YouCompleteMe
```
make install_ycm  # This will ask for your password
```

### Linux
1. Install development tools, CMake, Python headers, and Node.js
```
sudo apt-get install build-essential cmake python-dev nodejs
```

2. Install YouCompleteMe
```
make install_ycm  # This will ask for your password
```

And that's it!
