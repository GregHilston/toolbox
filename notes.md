# Notes

## To figure out

- Where to put the following script to disable auto folding
    - command 
    - from https://github.com/plasticboy/vim-markdown#set-header-folding-level

## Vim

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

### Fzf + Ripgrep

- hotkeyed ; to use fzf
    - From inside the menu, fzf will automatically detect ctrl-t to open the file in a new tab, ctrl-v for a vertical split or ctrl-x for a horizontal split.
- to open tabs 
    - From inside the menu, fzf will automatically detect ctrl-t to open the file in a new tab, ctrl-v for a vertical split or ctrl-x for a horizontal split.
    - From the terminal, you can do vim -p filename1 filename2 to open the two files in tabs.
- basically use fzf, hotkeyed to ;, to search for file names
- use rp, :Rg, to search contents of files

### NerdTree

- Open/Close Nerdtree with :NerdTree and :NerdTreeClose respectively
- Have a hotkey set for CTRL + o

### tmux 

- To reload confiuguration This can be done either from within tmux, by pressing Ctrl+B and then : to bring up a command prompt, and typing:
  - :source-file ~/.tmux.conf
  - Or simply from a shell:
  - $ tmux source-file ~/.tmux.conf
- to move windows use the hotkey we added to our tmux.conf
    - ctrl + shift + left to move to the left
    - ctrl + shift + right to move to the right
- to toggle fullscreen on a pane ctrl + b + z

### plasticboy/vim-markdown

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
- Try :help fold-expr and :help fold-commands for details.
