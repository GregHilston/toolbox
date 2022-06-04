"                 _               __      __ _____  __  __ 
"                | |              \ \    / /|_   _||  \/  |
" __      __ ___ | | _ __    ___   \ \  / /   | |  | \  / |
" \ \ /\ / // _ \| || '_ \  / _ \   \ \/ /    | |  | |\/| |
"  \ V  V /|  __/| || |_) ||  __/    \  /    _| |_ | |  | |
"   \_/\_/  \___||_|| .__/  \___|     \/    |_____||_|  |_|
"                   | |                                    
"                   |_|                  
" ------------------------------------------------------------------------------
" File: welpe.vim
" Description: vim colorscheme, loosely based on jellybeans, solarized-dark
" Author: Timm Stelzer <timmstelzer@gmail.com>
" Source: https://github.com/tstelzer/welpe.vim
" ------------------------------------------------------------------------------
"  TODO lighter foreground
"  TODO error unreadable
"  TODO statusline too bright
"  TODO differentiate operators 
"  TODO t16 and t8 cursorcolor (fg)
"  TODO lightline colorscheme

set background=dark

hi clear

if exists("syntax_on")
  syntax reset
endif

let colors_name = "welpe"
if !exists('g:welpe_all_bold')
    let g:welpe_all_bold = 0
endif
if !exists('g:welpe_use_italics')
    let g:welpe_use_italics = 0
endif

function! s:H(group,fg,bg,style) "{{{
" group = Syntax Group
" :help syntax
" fg = Foreground Color
" bg = Background Color
" style = Font Style

if &t_Co == 8 && exists(a:fg[2]) && exists(a:bg[2])

    let l:cbg = 0

    if !empty(a:fg)
        " foreground is NOT empty
        let l:cfg = a:fg[2]
    else 
        "foreground IS empty
        let l:cfg = "NONE"
    endif
    exec "hi ".a:group." ctermfg = ".l:cfg." ctermbg = ".l:cbg

else

    if !empty(a:fg)
        " foreground is NOT empty
        let l:gfg = a:fg[0]
        let l:cfg = a:fg[1]
    else
        let l:gfg = "NONE"
        let l:cfg = "NONE"
    endif

    if !empty(a:bg)
        " background is NOT empty
        let l:gbg = a:bg[0]
        let l:cbg = a:bg[1]
    else
        " background IS empty
        let l:gbg = "NONE"
        let l:cbg = "NONE"
    endif

    if g:welpe_all_bold == 1
        " all text is rendered bold
        let l:gstyle = "bold"
        let l:cstyle = "bold"
    else
        if !empty(a:style)
            if a:style == "italic" && g:welpe_use_italics == 0
                " no italics should be used
                let l:gstyle = "NONE"
                let l:cstyle = "NONE"
            else
                " style is NOT empty
                let l:gstyle = a:style
                let l:cstyle = a:style
                " TODO check if style works in TERM
            endif
        else
            " style IS empty
            let l:gstyle = "NONE"
            let l:cstyle = "NONE"
        endif
    endif
    " hi "<Syntax group>" guifg = "<fgcolor>" guibg = "<bgcolor>" 
    " \ ctermfg = "<termfg>" ctermbg = "<termbg>" 
    " \ gui = "<guistyle>" term = "<termstyle>"
    exec "hi ".a:group." guifg=".l:gfg." ctermfg=".l:cfg." guibg=".l:gbg.
                \ " ctermbg=".l:cbg." gui=".l:gstyle." term=".l:cstyle
endif
endfun
"}}}

" ##############################################################################
" ### #COLORPALETTE
" ##############################################################################
" Important: DO NOT CHANGE THESE VALUES, ONLY ADD NEW ONES
" Schema: s:<name> = [ '<hex>', <256term>, <16term>, <8term> ]

" --- Grayscale"{{{
" ------------------------------------------------------------------------------

let s:trueblack = [ '#000000', 16,  0,  0 ]
let s:black     = [ '#080808', 232, 0,  0 ]
let s:gray1     = [ '#121212', 233, 0,  7 ]
let s:gray2     = [ '#1c1c1c', 234, 0,  7 ]
let s:gray3     = [ '#262626', 235, 0,  7 ]
let s:gray4     = [ '#303030', 236, 8,  7 ]
let s:gray5     = [ '#3a3a3a', 237, 8,  7 ]
let s:gray6     = [ '#444444', 238, 8,  7 ]
let s:gray7     = [ '#4e4e4e', 239, 8,  7 ]
let s:gray8     = [ '#606060', 241, 8,  7 ]
let s:gray9     = [ '#666666', 242, 8,  7 ]
let s:gray10    = [ '#767676', 243, 8,  7 ]
let s:gray11    = [ '#808080', 244, 8,  7 ]
let s:gray12    = [ '#8a8a8a', 245, 7,  7 ]
let s:gray13    = [ '#949494', 245, 7,  7 ]
let s:gray14    = [ '#9e9e9e', 246, 7,  7 ]
let s:gray15    = [ '#9e9e9e', 247, 7,  7 ]
let s:gray16    = [ '#a8a8a8', 248, 7,  7 ]
let s:gray17    = [ '#b2b2b2', 249, 7,  7 ]
let s:gray18    = [ '#bcbcbc', 250, 7,  7 ]
let s:gray19    = [ '#c0c0c0', 7,   7,  7 ]
let s:gray20    = [ '#c6c6c6', 251, 7,  7 ]
let s:gray21    = [ '#d0d0d0', 252, 15, 7 ]
let s:gray22    = [ '#dadada', 253, 15, 7 ]
let s:gray23    = [ '#e4e4e4', 254, 15, 7 ]
let s:white     = [ '#eeeeee', 255, 15, 7 ]
let s:truewhite = [ '#FFFFFF', 15,  15, 7 ]
"}}}
" --- Colors {{{
" ------------------------------------------------------------------------------
" Important: DON'T USE THE COLORNAMES IN THE SYNTAX GROUPS,
" use the generic color vars instead

let s:roman      = [ '#d75f5f', 167, 1, 1 ]
let s:_darkred = s:roman
let s:sundown    = [ '#ffafaf', 217, 9, 1 ]
let s:_lightred = s:sundown

let s:laurel     = [ '#5f875f', 65, 2, 2 ]
let s:_darkgreen = s:laurel
let s:moss       = [ '#afd7af', 151, 10, 2 ]
let s:_lightgreen = s:moss

let s:rajah      = [ '#ffaf5f', 215, 3, 3 ]
let s:_orange = s:rajah
let s:canary     = [ '#ffffaf', 229, 11, 3 ]
let s:_yellow = s:canary

let s:cornflower   = [ '#5f87ff', 69, 4, 4 ]
let s:_darkblue = s:cornflower
let s:columbia   = [ '#afd7ff', 153, 12, 4 ]
let s:_lightblue = s:columbia

let s:darkviolet = [ '#8700df', 92, 5, 5 ]
let s:_darkmagenta = s:darkviolet
let s:thistle      = [ '#d7afd7', 182, 13, 5 ]
let s:_lightmagenta = s:thistle

let s:aquamarine = [ '#87ffd7', 122, 6, 6 ]
let s:_darkcyan = s:aquamarine
let s:lightcyan  = [ '#d7ffff', 195, 14, 6 ]
let s:_lightcyan = s:lightcyan

" }}}
" --- Discard Pile"{{{
" ------------------------------------------------------------------------------
let s:lavenderrose = [ '#ffafff', 219, 13, 5 ]
let s:cosmos     = [ '#ffd7d7', 224, 13, 5 ]
let s:mariner      = [ '#5f5faf', 61, 5, 5 ]
let s:mauve        = [ '#d7afff', 183, 13, 5 ]
let s:lavender     = [ '#afafd7', 146, 13, 5 ]
let s:maya         = [ '#87afff', 111, 4, 4 ]
let s:fountain     = [ '#5fafaf', 73, 4, 4 ]
let s:ziggurat     = [ '#87afaf', 109, 4, 4 ]
let s:quartz       = [ '#d7d7ff', 189, 13, 5 ]
let s:londonhue  = [ '#af87af', 139, 5, 5 ]
let s:jade         = [ '#00af5f', 35, 2, 2 ]
let s:sinbad       = [ '#afd7d7', 152, 4, 4 ]
let s:chill        = [ '#5f8787', 66, 6, 6 ]
let s:forest       = [ '#00875F', 29, 10, 2 ]
let s:biloba       = [ '#af87d7', 140, 5, 5 ]
let s:mantis       = [ '#87d75f', 113, 10, 2 ]
let s:olive        = [ '#afaf5f', 143, 10, 2 ]
let s:darkgreen    = [ '#005F00', 22, 2, 2 ]
let s:mint         = [ '#afff87', 156, 10, 2 ]
let s:lagoon       = [ '#005f87', 24, 12, 4 ]
let s:orange       = [ '#ffaf00', 214, 3, 3 ]
let s:tapestry     = [ '#af5f87', 132, 13, 5 ]
let s:maroon       = [ '#5f0000', 52, 1, 7 ]
let s:darkviolet   = [ '#af00d7', 128, 5, 5 ]
let s:manatee    = [ '#8787af', 103, 4, 4 ]
let s:pumpkin      = [ '#ff8700', 208, 3, 3 ]
let s:mosque       = [ '#005f5f', 23, 10, 2 ]
let s:gold         = [ '#ffd700', 220, 11, 3 ]
let s:bittersweet  = [ '#ff5f5f', 203, 9, 1 ]
let s:freespeech   = [ '#af0000', 124, 9, 1 ]
let s:venetian     = [ '#d70000', 160, 9, 1 ]
let s:citrus       = [ '#afaf00', 142, 3, 3 ]
let s:goldenbrown  = [ '#af5f00', 130, 13, 5 ]
let s:green        = [ '#008700', 28, 10, 2 ]
let s:darkblue     = [ '#000087', 18, 4, 4 ]
let s:salmon       = [ '#ff8787', 210, 13, 5 ]
"}}}


" ##############################################################################
" ### #FUNCTIONAL VARIABLES
" ##############################################################################
" change the assigned variables, if you want to change the presented colors

" --- Custom fields {{{
let s:lightfg = s:white 
" lighter version of foreground
let s:fg = s:gray22
" default foreground
let s:darkfg = s:gray18
" darker version of foreground

let s:lightbg = s:gray5
" lighter version of foreground
let s:bg = s:gray2
" default background
let s:darkbg = s:gray1
" darker version of foreground

let s:positive   = s:_lightgreen
" used for anything related to adding, positive values etc
let s:neutral    = s:_lightblue
" neutral color, used for neither positive nor negative
let s:negative   = s:_lightred
" used for negative values, substraction, errors etc

let s:comment        = s:gray11
" besides comments, used for any neutral-gray
"}}}

" ##############################################################################
" ### #HIGHLIGHTING
" ##############################################################################
" Schema: see function s:H()
" s:h(<SyntaxGroup>!, <foreground>, <background>, <style>)
" Note: if you ommit fields with "", the default fg / bg will be inherited
" Note: entirely omitted groups fallback to their parent
" for example "Function" inherits "Identifier" by default

" --- UI Defaults {{{
" ------------------------------------------------------------------------------

call s:H("Normal",       s:fg,        s:bg,       "")
" default values
" omitted values inherit this 

call s:H("ColorColumn",  "",          s:darkbg,  "")
" set colorcolumn = <column numbers>
" vertical colored line, used to align text or not go over a certain textwidth
call s:H("Conceal",      s:_darkblue,   "",         "")
" set conceallevel = <0-3>
call s:H("Cursor",       s:darkbg,        s:lightfg,       "")
" blinking cursor
call s:H("CursorColumn", "",          s:lightbg,  "")
" vertical highlight of current cursor position
call s:H("CursorLine",   "",          s:lightbg,  "")
" horizontal highlight of current cursor position
call s:H("CursorLineNr", s:lightfg,   s:darkbg,   "bold")
" linenumber of cursor position

call s:H("DiffAdd",      s:positive,  s:lightbg,  "")
call s:H("DiffChange",   s:neutral,   s:lightbg,  "")
call s:H("DiffDelete",   s:negative,  s:lightbg,  "")
" diff mode
call s:H("Directory",    s:_lightblue,  "",         "")
" directory names and other special names in listings

call s:H("ErrorMsg",     s:_yellow,    s:negative, "")
" generic error message

call s:H("FoldColumn",   "",          s:lightbg,  "")
" set foldcolumn = 1
" gutter for folds
call s:H("Folded",       s:lightfg,   s:lightbg,  "")
" line highlight for closed folds

call s:H("IncSearch",    s:_orange,     "",         "")
" set incearch
" highlight for search queries

call s:H("LineNr",       s:comment,   s:darkbg,   "")
" set number, and/or set relativenumber
" number gutter

call s:H("MatchParen",   s:white,     s:darkbg,   "bold")
call s:H("ModeMsg",      s:_lightblue,  s:darkbg,   "")
call s:H("MoreMsg",      s:_lightblue,  s:darkbg,   "")
call s:H("NonText",      s:_orange,     "",         "")
" set showbreak = <char>
" characters that visualize linebreaks, tabs etc.

call s:H("Pmenu",        "",          "",         "")
" popup menu
call s:H("PmenuSbar",    "",          s:darkbg,   "")
" popup menu scrollbar
call s:H("PmenuSel",     s:_orange,     s:lightbg,  "")
" popup menu selected text
call s:H("PmenuThumb",   "",          "",         "")
" popup menu thumb of scrollbar

call s:H("Question",     s:_lightcyan, s:darkbg,   "bold")
" 'hit-enter' prompt and yes/no questions

call s:H("Search",       s:_yellow,    "",         "")
" set hlsearch
" highlight of last search query
" also used for current line in quickfix
call s:H("SignColumn",   "",          s:darkbg,   "")
" sign gutter
call s:H("SpecialKey",   s:_orange,     "",         "bold")
" :help listchars
" non-text chars like mappings, eol-characters, nbsp etc.
call s:H("SpelBad",      s:negative,  "",         "undercurl")
" unrecognized by spellchecker
call s:H("SpellRare",    s:neutral,   "",         "undercurl")
" rare word
call s:H("SpellCap",     s:_darkmagenta, "",         "undercurl")
" should be starting with a capital letter
call s:H("SpellLocal",   s:_yellow,    "",         "undercurl")
" recognized as from another locale
call s:H("StatusLine",   s:lightfg,   s:lightbg,  "")
" set lastshow = <0-2>
" statusline of current window
call s:H("StatusLineNC", s:darkfg,    s:darkbg,   "")
" statusline of non-current window

call s:H("TabLineSel",   s:lightfg,   s:darkbg,   "bold")
" active tabpage label
call s:H("TabLine",      s:lightfg,   s:lightbg,  "")
" nonactive tabpage label
call s:H("TabLineFill",  s:darkfg,    s:lightbg,  "")
" background of tabline, no labels
call s:H("Title",        s:_orange,     "",         "bold")
" titles, i guess? no idea
" doc says 'titles for output from :set all, :autocmd etc.'

call s:H("VertSplit",    s:comment,   s:darkbg,   "")
" column separating splits
call s:H("Visual",       s:darkbg,   s:darkfg,  "")
" visually selected lines

call s:H("WildMenu",     s:_lightmagenta,    "",         "")
" current match in wildmenu completion
call s:H("WarningMsg",   s:negative,  "",         "bold")
" warning messages
" }}}
" --- Default Syntax Groups {{{
" ------------------------------------------------------------------------------
" VIM classifes MAJOR and MINOR syntax groups
" by default, every MINOR inherits its MAJORS values
" uncomment the function call to specify the MINORS values

call s:H("Comment",        s:comment,        "",         "italic")

call s:H("Constant",       s:_darkcyan,     "",         "")
" --- MINORS of Constant:
"
call s:H("String",         s:_lightgreen,         "",         "")
" any string
" inherits constant by default
"
hi! link Character String
" call s:H("Character",      s:character,      "",         "")
" any single character: 'c', '\n'
" inherits constant by default

call s:H("Number",         s:_lightcyan,      "",         "bold")
" any number, including unit
" inherits constant by default

" call s:H("Boolean",        s:boolean,        "",         "")
" any boolean: TRUE, false
" inherits constant by default

" call s:H("Float",          s:float,          "",         "")
hi! link Float Number
" a floating point constant: 2.3e10
" inherits constant by default

call s:H("Identifier",     s:_lightmagenta,        "",         "")
" any variable name
" --- MINORS of Identifier:

call s:H("Function",       s:_lightblue,       "",         "")
" any function, method, class
" inherits identifier by default

call s:H("Statement",      s:_darkblue,         "",         "")
" any statement
" --- MINORS of Identifier: 

" call s:H("Conditional",    s:statement,      "",         "")
" if, then, else, endif, switch, etc.
" inherits statement by default

" call s:H("Repeat",         s:repeat,         "",         "")
" for, do, while, etc.
" inherits statement by default

" call s:H("Label",          s:label,          "",         "")
" case, default, etc.
" inherits statement by default

" call s:H("Operator",       s:operator,       "",         "")
" "sizeof", "+", "*", etc.
" inherits statement by default

" call s:H("Keyword",        s:keyword,        "",         "")
" any other keyword
" inherits statement by default

" call s:H("Exception",      s:exception,      "",         "")
" try, catch, throw
" inherits statement by default

call s:H("PreProc",        s:_lightcyan,      "",         "italic")
" generic preprocessor
" --- MINORS of PreProc:

" call s:H("Include",        s:include,        "",         "")
" inherits preproc by default

" call s:H("Define",         s:define,         "",         "")
" inherits preproc by default

" call s:H("Macro",          s:macro,          "",         "")
" inherits preproc by default

" call s:H("PreCondit",      s:precondit,      "",         "")
" inherits preproc by default

call s:H("Type",           s:_yellow,         "",         "")
" int, long, char, etc.
" --- MINORS of Type:

" call s:H("StorageClass",   s:storageclass,   "",         "")
" static, register, volatile, etc.
" inherits type by default

" call s:H("Structure",      s:structure,      "",         "")
" struct, union, enum, etc.
" inherits type by default

" call s:H("Typedef",        s:typedef,        "",         "")
" A typedef
" inherits type by default

call s:H("Special",        s:_orange,          "",         "")
" any special symbol
" --- MINORS of Special

" call s:H("SpecialChar",    s:specialchar,    "",         "")
" inherits special by default

" call s:H("Tag",            s:tag,            "",         "")
" inherits special by default

call s:H("Delimiter",      s:_darkred,      "",         "")
" inherits special by default

" call s:H("SpecialComment", s:specialcomment, "",         "")
" inherits special by default

call s:H("Debug",          s:neutral,          "",         "")
" inherits special by default

call s:H("Underlined",     s:_lightmagenta,         "",         "")

call s:H("Ignore",         "",               "",         "")

call s:H("Error",          s:_yellow,         s:negative, "bold")

call s:H("Todo",           s:lightfg,        s:lightbg,  "bold")
" }}}
" --- Filetype specific Syntax {{{
" ------------------------------------------------------------------------------
" Vimscript"{{{
"
hi! link vimSet Normal
hi! link vimSetEqual Normal
hi! link vimVar Identifier
hi! link vimFunc Function
hi! link vimUserFunc Function
hi! link vimIsCommand Statement
hi! link vimOperParen Identifier
hi! link helpSpecial Special
hi! link vimCommentString String
hi! link vimCommentTitle Title
" vimCommand       
" vimCmdSep        
" helpExample      
" helpOption       
" helpNote         
" helpVim          
" helpHyperTextJump
" helpHyperTextEntry
" vimIsCommand     
" vimSynMtchOpt    
" vimSynType       
" vimHiLink        
" vimHiGroup       
" vimGroup         
"}}}
" HTML"{{{
call s:H("htmlBold",        "",               "",           "bold")
call s:H("htmlItalic",      "",               "",           "italic")
" htmlTag          
" htmlEndTag       
" htmlTagN         
" htmlTagName      
" htmlSpecialTagName
" htmlArg          
" javaScript       
" }}}
" CSS / SASS {{{
" ------------------------------------------------------------------------------
"HiLink cssComment Comment
hi! link cssVendor cssProp
"HiLink cssHacks Comment
"HiLink cssTagName Statement
"HiLink cssDeprecated Error
"HiLink cssSelectorOp Special
"HiLink cssSelectorOp2 Special
"HiLink cssAttrComma Special

"HiLink cssAnimationProp cssProp
"HiLink cssBackgroundProp cssProp
"HiLink cssBorderProp cssProp
"HiLink cssBoxProp cssProp
"HiLink cssColorProp cssProp
"HiLink cssContentForPagedMediaProp cssProp
"HiLink cssDimensionProp cssProp
"HiLink cssFlexibleBoxProp cssProp
"HiLink cssFontProp cssProp
"HiLink cssGeneratedContentProp cssProp
"HiLink cssGridProp cssProp
"HiLink cssHyerlinkProp cssProp
"HiLink cssLineboxProp cssProp
"HiLink cssListProp cssProp
"HiLink cssMarqueeProp cssProp
"HiLink cssMultiColumnProp cssProp
"HiLink cssPagedMediaProp cssProp
"HiLink cssPositioningProp cssProp
"HiLink cssPrintProp cssProp
"HiLink cssRubyProp cssProp
"HiLink cssSpeechProp cssProp
"HiLink cssTableProp cssProp
"HiLink cssTextProp cssProp
"HiLink cssTransformProp cssProp
"HiLink cssTransitionProp cssProp
"HiLink cssUIProp cssProp
"HiLink cssIEUIProp cssProp
"HiLink cssAuralProp cssProp
"HiLink cssRenderProp cssProp
"HiLink cssMobileTextProp cssProp

"HiLink cssAnimationAttr cssAttr
"HiLink cssBackgroundAttr cssAttr
"HiLink cssBorderAttr cssAttr
"HiLink cssBoxAttr cssAttr
"HiLink cssContentForPagedMediaAttr cssAttr
"HiLink cssDimensionAttr cssAttr
"HiLink cssFlexibleBoxAttr cssAttr
"HiLink cssFontAttr cssAttr
"HiLink cssGeneratedContentAttr cssAttr
"HiLink cssGridAttr cssAttr
"HiLink cssHyerlinkAttr cssAttr
"HiLink cssLineboxAttr cssAttr
"HiLink cssListAttr cssAttr
"HiLink cssMarginAttr cssAttr
"HiLink cssMarqueeAttr cssAttr
"HiLink cssMultiColumnAttr cssAttr
"HiLink cssPaddingAttr cssAttr
"HiLink cssPagedMediaAttr cssAttr
"HiLink cssPositioningAttr cssAttr
"HiLink cssGradientAttr cssAttr
"HiLink cssPrintAttr cssAttr
"HiLink cssRubyAttr cssAttr
"HiLink cssSpeechAttr cssAttr
"HiLink cssTableAttr cssAttr
"HiLink cssTextAttr cssAttr
"HiLink cssTransformAttr cssAttr
"HiLink cssTransitionAttr cssAttr
"HiLink cssUIAttr cssAttr
"HiLink cssIEUIAttr cssAttr
"HiLink cssAuralAttr cssAttr
"HiLink cssRenderAttr cssAttr
"HiLink cssCommonAttr cssAttr

"HiLink cssPseudoClassId PreProc
"HiLink cssPseudoClassLang Constant
"HiLink cssValueLength Number
"HiLink cssValueInteger Number
"HiLink cssValueNumber Number
"HiLink cssValueAngle Number
"HiLink cssValueTime Number
"HiLink cssValueFrequency Number
"HiLink cssFunction Constant
"HiLink cssURL String
"HiLink cssFunctionName Function
"HiLink cssFunctionComma Function
"HiLink cssColor Constant
"HiLink cssIdentifier Function
"HiLink cssInclude Include
"HiLink cssIncludeKeyword atKeyword
"HiLink cssImportant Special
hi! link cssBraces Delimiter " test
"HiLink cssBraceError Error
"HiLink cssError Error
"HiLink cssUnicodeEscape Special
"HiLink cssStringQQ String
"HiLink cssStringQ String
"HiLink cssAttributeSelector String
"HiLink cssMedia atKeyword
"HiLink cssMediaType Special
"HiLink cssMediaComma Normal
"HiLink cssMediaKeyword Statement
"HiLink cssMediaProp cssProp
"HiLink cssMediaAttr cssAttr
"HiLink cssPage atKeyword
"HiLink cssPagePseudo PreProc
"HiLink cssPageMargin atKeyword
"HiLink cssPageProp cssProp
"HiLink cssKeyFrame atKeyword
"HiLink cssKeyFrameSelector Constant
"HiLink cssFontDescriptor Special
"HiLink cssFontDescriptorFunction Constant
"HiLink cssFontDescriptorProp cssProp
"HiLink cssFontDescriptorAttr cssAttr
"HiLink cssUnicodeRange Constant
"HiLink cssClassName Function
"HiLink cssClassNameDot Function
"HiLink cssProp StorageClass
"HiLink cssAttr Constant
hi! link cssUnitDecorators Delimiter
"HiLink cssNoise Noise
"HiLink atKeyword PreProc

" }}}
" Autohotkey {{{
" hi def link autohotkeyHotkey              Type
" hi def link autohotkeyKey                 Type
" hi def link autohotkeyDelimiter           Delimiter
" hi def link autohotkeyHotstringDefinition Type
" hi def link autohotkeyHotstring           Type
" hi def link autohotkeyHotstringDelimiter  autohotkeyDelimiter
" hi def link autohotkeyHotstringOptions    Special
" hi def link autohotkeyString              String
" hi def link autohotkeyStringDelimiter     autohotkeyString
" hi def link autohotkeyVariable            Identifier
" hi def link autohotkeyVariableDelimiter   autohotkeyVariable
" hi def link autohotkeyBuiltinVariable     Macro
" hi def link autohotkeyCommand             Keyword
" hi def link autohotkeyFunction            Function
" hi def link autohotkeyStatement           autohotkeyCommand
" hi def link autohotkeyRepeat              Repeat
" hi def link autohotkeyConditional         Conditional
" hi def link autohotkeyPreProcStart        PreProc
" hi def link autohotkeyInclude             Include
" hi def link autohotkeyPreProc             PreProc
" hi def link autohotkeyMatchClass          Typedef
" hi def link autohotkeyNumber              Number
" hi def link autohotkeyInteger             autohotkeyNumber
" hi def link autohotkeyFloat               autohotkeyNumber
" hi def link autohotkeyType                Type
" hi def link autohotkeyBoolean             Boolean
"}}}
" diff highlighting "{{{
" ---------------------------------------------------------------------
hi! link diffAdded Statement
hi! link diffLine Identifier
"}}}
" git & gitcommit highlighting "{{{

" gitDateHeader
" gitIdentityHeader
" gitIdentityKeyword
" gitNotesHeader
" gitReflogHeader
" gitKeyword
" gitIdentity
" gitEmailDelimiter
" gitEmail
" gitDate
" gitMode
" gitHashAbbrev
" gitHash
" gitReflogMiddle
" gitReference
" gitStage
" gitType
" gitDiffAdded
" gitDiffRemoved
" gitcommit
" gitcommitSummary
" gitcommitComment
" gitcommitUntracked 
" gitcommitDiscarded 
" gitcommitSelected  
" gitcommitUnmerged
" gitcommitOnBranch
" gitcommitBranch
" gitcommitNoBranch
" gitcommitDiscardedType
" gitcommitSelectedType
" gitcommitUnmergedType
" gitcommitType
" gitcommitNoChanges
" gitcommitHeader
" gitcommitHeader
" gitcommitUntrackedFile
" gitcommitDiscardedFile
" gitcommitSelectedFile
" gitcommitUnmergedFile
" gitcommitFile
" gitcommitDiscardedArrow
" gitcommitSelectedArrow 
" gitcommitUnmergedArrow 
" gitcommitArrow
" gitcommitOverflow
" gitcommitBlank
" }}}
" NERDTree {{{
" ------------------------------------------------------------------------------

" }}}
" }}}

delf s:H
" delete highlight function
