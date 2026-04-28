-- Disable nvim-treesitter due to build issues with query_predicates module
return {
  { "nvim-treesitter/nvim-treesitter", enabled = false },
  { "nvim-treesitter/nvim-treesitter-textobjects", enabled = false },
}
