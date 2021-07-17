" :help [command] for more information 
scriptencoding utf-8
set encoding=utf-8

" ============================================================================
" Initialize plugins
" ============================================================================
call plug#begin('~/.local/share/nvim/plugged')

" Editor
Plug 'junegunn/fzf', { 'do': { -> fzf#install() } } " fuzzy file search
Plug 'junegunn/fzf.vim'
Plug 'itchyny/lightline.vim' 	        " pretty status bar
Plug 'preservim/nerdtree' 	            " pretty file tree
Plug 'airblade/vim-gitgutter' 	        " git status on left hand column of files in a git repo
Plug 'tpope/vim-fugitive' 	            " to run git commands in vim
Plug 'tpope/vim-surround' 	            " to change surronding blocks
Plug 'w0rp/ale'			                " running linting in vim
Plug 'tpope/vim-fugitive'               " somewhat of a wrapper for Git in vim
Plug 'tpope/vim-surround'                " surronding parentheses, brackets, quoates, XMl, etc...
Plug 'scrooloose/syntastic'             " syntax checking for many languages
Plug 'godlygeek/tabular'                " for lining up text
Plug 'christoomey/vim-tmux-navigator'   " seamless navigation between tmux panes and vim splits
Plug 'bronson/vim-trailing-whitespace'  " highlights and removes trailing whitespace
Plug 'bogado/file-line'                 " allows `$ file:line` to open vim at a specific line
Plug 'tpope/vim-eunuch'                 " adds unix commands within vim like sudowrite, chmod and rename
Plug 'preservim/nerdcommenter'          " allows ctrl + / to comment or uncommentc
Plug 'kamykn/popup-menu.nvim'            " advanced spell check

" Language
" ----- Python -----
Plug 'nvie/vim-flake8' 		" runs flake8 against python file
Plug 'davidhalter/jedi-vim' " python autocomplete

" ----- Markdown -----
Plug 'dkarter/bullets.vim' 	" auto creates bulleted lists for markdown files
Plug 'godlygeek/tabular'
Plug 'plasticboy/vim-markdown'

" ----- HTML/CSS/JS -----
Plug 'mattn/emmet-vim'      " auto completion for html/css/js

call plug#end()

" enabling plugin syntastic to use mypy for us
let g:syntastic_python_checkers=['mypy']

let g:vim_markdown_override_foldtext = 0

" Picking list indicators for bullets vim plugin
let g:bullets_enabled_file_types = [
    \ 'markdown',
    \ 'text',
    \ 'gitcommit',
    \ 'scratch'
    \]

" Making CTRL + SPACE use jedi-vim for auto complete
" From here https://kevinmartinjose.com/2020/11/22/vimcharm-approximating-pycharm-on-vim/
let jedi#show_call_signatures = 0
let jedi#documentation_command = ""
autocmd FileType python setlocal completeopt-=preview

" Making CTRL + CLICK go to definition using jedi-vim
" Also enables opening a new tab when navigating to a different file
" From here https://kevinmartinjose.com/2020/11/22/vimcharm-approximating-pycharm-on-vim/
set mouse=a
let g:jedi#goto_command = "<C-LeftMouse>"
map <C-b> <C-LeftMouse>

let g:jedi#use_tabs_not_buffers = 1
nnoremap J :tabp<CR>
nnoremap K :tabn<CR>

" Making CTRL + / comment and uncomment lines using nerdcommenter
" From here https://kevinmartinjose.com/2020/11/22/vimcharm-approximating-pycharm-on-vim/
" The part after "=" in the below line should be inserted using Ctrl+v while in insert mode and then pressing Ctrl+/
set <F13>=^_
noremap <F13> :call NERDComment(0,"toggle")<CR>

" So that NERDCommenter can automatically decide how to comment a particular filetype
filetype plugin on

" Enable lightline
set laststatus=2
" disable redundant insert display
set noshowmode

" map fzf to shift + ;
" map ; :Files<CR>

" map ripgrep with fzf to ;
: map ; :Rg<CR>

" have fzf use ripgrep
set grepprg=rg\ --vimgrep\ --smart-case\ --hidden\ --follow

" allow ctrl left/right h/j switch between tabs
nnoremap <C-Left> :tabprevious<CR>                                                                            
nnoremap <C-Right> :tabnext<CR>
nnoremap <C-j> :tabprevious<CR>                                                                            
nnoremap <C-k> :tabnext<CR>

" map nerd Tree to CTRL + o
map <C-o> :NERDTreeToggle<CR>

" setting vim title bar to name of file and time of last modification
set title
set titlestring=%{hostname()}\ \ %F\ \ %{strftime('%Y-%m-%d\ %H:%M',getftime(expand('%')))}

" ============================================================================
" Editor config
" ============================================================================
" Visual Changes
colorscheme elflord
syntax enable     " Turn on syntax highlighting
syntax on
set number        " Shows lines numbers along left side
set ruler         " Shows file stats in bottom right corner
set visualbell    " Blink cursor on error instead of beeping 
set cursorline    " Highlights current line
set wildmenu      " Visual autocomplete for command menu
" Italicize comments
highlight Comment cterm=italic gui=italic
set linespace=4 " Set line height
" set title 	" Set title of window to file name

" Last line
set showcmd       " Shows command in bottom bar

" Searching
set incsearch     " Searches as characters are entered
set hlsearch      " Highlights matches
set ignorecase    " Ignores cases of characters to match
set showmatch     " Highlights matching [{()}]

" Set automatic indentation
set autoindent
set smartindent

" Set tabs at 4 spaces
set tabstop=4     " Number of spaces a tab counts for visually
set softtabstop=4 " Number of spaces a tab counts for when inserting/deleting
set expandtab     " Tabs are spaces
set cindent
set sw=4 ts=4 et
set hlsearch
set incsearch

set pastetoggle=<F3> " toggle paste mode with f3, paste mode is a special insert mode that lets you pate configs/code without auto indenting or commenting lines

" Disable arrow keys for movemnet in normal mode (From this link https://vi.stackexchange.com/a/5854)
noremap <Up> <Nop>
noremap <Down> <Nop>
noremap <Left> <Nop>
noremap <Right> <Nop>

" From this link
" https://github.com/vim/vim/issues/1326#issuecomment-266955735
set mouse-=a

" disables built in spellcheck to use our plugin
set nospell
