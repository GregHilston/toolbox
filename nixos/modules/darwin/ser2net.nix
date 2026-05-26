{vars, ...}: {
  # Expose USB serial devices (Zigbee/Z-Wave sticks) over TCP via ser2net.
  # OrbStack has no USB passthrough, so Docker containers connect to these
  # TCP sockets instead. See ~/Git/home-lab/docs/usb-passthrough-orbstack.md.
  #
  # Ports:
  #   20108 — Zigbee coordinator (zigbee2mqtt connects here)
  #   20109 — Z-Wave controller (Z-Wave JS UI connects here)
  #
  # Config: ~/.config/ser2net/ser2net.yaml (deployed via stow)
  launchd.user.agents.ser2net = {
    command = "/opt/homebrew/opt/ser2net/sbin/ser2net -n -c /Users/${vars.user.name}/.config/ser2net/ser2net.yaml";
    serviceConfig = {
      RunAtLoad = true;
      KeepAlive = true;
      StandardOutPath = "/Users/${vars.user.name}/Library/Logs/ser2net.log";
      StandardErrorPath = "/Users/${vars.user.name}/Library/Logs/ser2net.log";
    };
  };
}
