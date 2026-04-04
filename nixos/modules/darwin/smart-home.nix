{
  vars,
  pkgs,
  lib,
  ...
}: let
  # Config directories mirror the SERVER_CONFIG_BASE convention used by the
  # home-lab docker-compose stack: /Users/ghilston/home-lab-config/<service>/.
  # Z2M and Z-Wave JS UI run NATIVELY on dungeon (not in OrbStack) because
  # OrbStack's Linux VM has no USB passthrough — the Zigbee coordinator and
  # Z-Wave controller are only visible to macOS as /dev/cu.usbserial-* devices.
  configBase = "/Users/${vars.user.name}/home-lab-config";
  z2mConfigDir = "${configBase}/zigbee2mqtt";
  zwaveConfigDir = "${configBase}/zwave-js-ui";

  # Optional secrets file. Schema (all keys optional):
  #   {
  #     "zigbee_serial_port": "/dev/cu.usbserial-XXXX",
  #     "zwave_serial_port":  "/dev/cu.usbserial-YYYY",
  #     "mqtt_user":          "...",   // omit for anonymous broker (current state)
  #     "mqtt_password":      "...",
  #     "zwavejs_session_secret": "<32-byte hex>"
  #   }
  # The file lives at nixos/secrets/smart-home.json and is gitignored. If
  # missing, defaults below are used (placeholder serial ports, no MQTT auth).
  secretsPath = ../../secrets/smart-home.json;
  secrets =
    if builtins.pathExists secretsPath
    then builtins.fromJSON (builtins.readFile secretsPath)
    else {};

  # Serial port placeholders. The real /dev/cu.usbserial-* paths will be
  # filled in once `ls /dev/cu.*` is run on dungeon. Until then, the launchd
  # daemons will start but Z2M / Z-Wave JS UI will fail to open the device
  # and KeepAlive will keep restarting them — that's fine, deliberate no-op.
  zigbeeSerialPort = secrets.zigbee_serial_port or "/dev/cu.usbserial-ZIGBEE_PLACEHOLDER";
  zwaveSerialPort = secrets.zwave_serial_port or "/dev/cu.usbserial-ZWAVE_PLACEHOLDER";

  # MQTT auth — mosquitto broker in the home-lab stack is currently anonymous,
  # so we omit credentials unless a secret is provided.
  mqttUser = secrets.mqtt_user or "";
  mqttPassword = secrets.mqtt_password or "";
  mqttHasAuth = mqttUser != "";

  # Z-Wave JS UI session secret — used to sign web-UI session cookies. If not
  # provided, Z-Wave JS UI will generate and persist its own on first run.
  zwavejsSessionSecret = secrets.zwavejs_session_secret or "";

  # Zigbee2MQTT configuration.yaml. Written to disk on first activation only
  # (see activation script below) so that manual edits — including filling in
  # the real serial port — survive subsequent `just dr dungeon` runs. To force
  # a re-render, delete the file on dungeon and re-activate.
  z2mConfigYaml = ''
    # Managed by nix-darwin on first activation only.
    # Source: nixos/modules/darwin/smart-home.nix
    # Safe to edit manually — subsequent activations will NOT overwrite this file.
    # To re-render from nix, delete this file and run `just dr dungeon`.

    homeassistant:
      enabled: true

    frontend:
      enabled: true
      port: 8080
      host: 0.0.0.0

    mqtt:
      server: mqtt://localhost:1883
      base_topic: zigbee2mqtt
      ${lib.optionalString mqttHasAuth "user: ${mqttUser}"}
      ${lib.optionalString mqttHasAuth "password: ${mqttPassword}"}

    serial:
      port: ${zigbeeSerialPort}

    advanced:
      network_key: GENERATE
      log_level: info
      log_output:
        - console

    permit_join: false
    availability: true
  '';

  z2mConfigFile = pkgs.writeText "zigbee2mqtt-configuration.yaml" z2mConfigYaml;
in {
  # Install binaries via Homebrew.
  #
  # Rationale: both Zigbee2MQTT and Z-Wave JS UI are Node.js apps with native
  # serialport bindings. nixpkgs derivations for these are Linux-first and
  # have historically been flaky on aarch64-darwin. Homebrew formulae
  # (`zigbee2mqtt`, `zwave-js-ui`) are actively maintained for Apple Silicon
  # and match this repo's existing pattern of installing server-class binaries
  # on dungeon via brew (orbstack, docker, tailscale).
  homebrew.brews = [
    "zigbee2mqtt"
    "zwave-js-ui"
  ];

  # Create config directories and seed the Z2M configuration.yaml (once).
  # Uses lib.mkAfter so this runs after the host's own postActivation block
  # (which creates home-lab-config/ and clones the home-lab repo).
  system.activationScripts.postActivation.text = lib.mkAfter ''
    # Smart home native services — config directories.
    sudo -H -u "${vars.user.name}" mkdir -p "${z2mConfigDir}" "${zwaveConfigDir}"

    # Seed Zigbee2MQTT configuration.yaml on first run only. Do NOT clobber
    # manual edits (the real serial port is filled in by hand post-deploy).
    if [ ! -f "${z2mConfigDir}/configuration.yaml" ]; then
      echo "Seeding ${z2mConfigDir}/configuration.yaml from nix..."
      cp ${z2mConfigFile} "${z2mConfigDir}/configuration.yaml"
      chown "${vars.user.name}:staff" "${z2mConfigDir}/configuration.yaml"
      chmod 644 "${z2mConfigDir}/configuration.yaml"
    fi
  '';

  # Zigbee2MQTT daemon.
  #
  # Publishes Zigbee device state to the mosquitto broker running in the
  # home-lab OrbStack stack. From this daemon's perspective (running on the
  # host, not in the VM) the broker is at localhost:1883 because OrbStack
  # forwards container ports to 127.0.0.1 on the host.
  #
  # HA (running inside OrbStack) auto-discovers Zigbee devices via MQTT
  # discovery on the zigbee2mqtt/ topic — no direct network path from HA
  # to this daemon is required.
  launchd.daemons.zigbee2mqtt = {
    serviceConfig = {
      ProgramArguments = [
        "/opt/homebrew/bin/zigbee2mqtt"
      ];
      EnvironmentVariables = {
        # Z2M reads configuration.yaml from $ZIGBEE2MQTT_DATA.
        ZIGBEE2MQTT_DATA = z2mConfigDir;
        PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin";
      };
      WorkingDirectory = z2mConfigDir;
      KeepAlive = true;
      RunAtLoad = true;
      # Don't thrash if the serial port placeholder is still in place.
      ThrottleInterval = 30;
      StandardOutPath = "/var/log/zigbee2mqtt.log";
      StandardErrorPath = "/var/log/zigbee2mqtt.log";
    };
  };

  # Z-Wave JS UI daemon.
  #
  # Exposes two TCP services, both bound to 0.0.0.0 so HA running inside
  # OrbStack can reach them via host.docker.internal (or the host's LAN IP):
  #   - 8091: web UI (for device inclusion, diagnostics, OZW-style admin)
  #   - 3000: WebSocket server, consumed by HA's Z-Wave integration
  #           (HA config: ws://<dungeon-lan-ip>:3000)
  #
  # All runtime state lives under STORE_DIR so snapshots / rsync of
  # /Users/ghilston/home-lab-config/zwave-js-ui/ capture the full Z-Wave
  # network cache.
  launchd.daemons.zwave-js-ui = {
    serviceConfig = {
      ProgramArguments = [
        "/opt/homebrew/bin/zwave-js-ui"
      ];
      EnvironmentVariables =
        {
          STORE_DIR = zwaveConfigDir;
          ZWAVEJS_EXTERNAL_CONFIG = "${zwaveConfigDir}/.config-db";
          # Web UI
          HOST = "0.0.0.0";
          PORT = "8091";
          # WebSocket server for HA's Z-Wave integration
          WS_HOST = "0.0.0.0";
          WS_PORT = "3000";
          # Serial device — placeholder until `ls /dev/cu.*` is run on dungeon.
          ZWAVEJS_DEVICE = zwaveSerialPort;
          USE_SECURE_COOKIE = "false";
          PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin";
        }
        // lib.optionalAttrs (zwavejsSessionSecret != "") {
          SESSION_SECRET = zwavejsSessionSecret;
        };
      WorkingDirectory = zwaveConfigDir;
      KeepAlive = true;
      RunAtLoad = true;
      ThrottleInterval = 30;
      StandardOutPath = "/var/log/zwave-js-ui.log";
      StandardErrorPath = "/var/log/zwave-js-ui.log";
    };
  };
}
