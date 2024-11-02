{ pkgs, inputs, ... }:

{
    programs.git = {
      enable = true;
      userName  = "GregHilston";
      userEmail = "Gregory.Hilston@gmail.com";
    };
}