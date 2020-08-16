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
Plug 'itchyny/lightline.vim' 	" pretty status bar
Plug 'preservim/nerdtree' 	" pretty file tree
Plug 'airblade/vim-gitgutter' 	" git status on left hand column of files in a git repo
Plug 'tpope/vim-fugitive' 	" to run git commands in vim
Plug 'tpope/vim-surround' 	" to change surronding blocks
Plug 'w0rp/ale'			" running linting in vim

" Language
" ----- Python -----
Plug 'nvie/vim-flake8' 		" runs flake8 against python file

" ----- Markdown -----
Plug 'dkarter/bullets.vim' 	" auto creates bulleted lists for markdown files
Plug 'godlygeek/tabular'
Plug 'plasticboy/vim-markdown'

call plug#end()

let g:vim_markdown_override_foldtext = 0

" Picking list indicators for bullets vim plugin
let g:bullets_enabled_file_types = [
    \ 'markdown',
    \ 'text',
    \ 'gitcommit',
    \ 'scratch'
    \]

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