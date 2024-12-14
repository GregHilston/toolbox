{ inputs, outputs, lib, config, pkgs, vars, ... }:

{
  imports = [
    ../../../modules/common
  ];

  networking.hostName = "foundation";
}
