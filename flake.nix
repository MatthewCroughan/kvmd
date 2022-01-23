{
  description = "The main Pi-KVM daemon";

  # Nixpkgs / NixOS version to use.
  inputs.nixpkgs.url = "github:nixos/nixpkgs/nixos-21.11";

  outputs = { self, nixpkgs }:
    let
      # Generate a user-friendly version number.
      version = builtins.substring 0 8 self.lastModifiedDate;
      # System types to support.
      supportedSystems = [ "x86_64-linux" "x86_64-darwin" "aarch64-linux" "aarch64-darwin" ];
      # Helper function to generate an attrset '{ x86_64-linux = f "x86_64-linux"; ... }'.
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
      # Nixpkgs instantiated for supported system types.
      nixpkgsFor = forAllSystems (system: import nixpkgs { inherit system; overlays = [ self.overlay ]; });
    in
    {
      # A Nixpkgs overlay.
      overlay = final: prev: {
        python39Packages = final.python39.pkgs;
        python39 = prev.python39.override {
          packageOverrides = self: super: {
            pyghmi = super.buildPythonPackage rec {
              pname = "pyghmi";
              version = "1.5.33";
              src = super.fetchPypi {
                inherit pname version;
                sha256 = "sha256-TV9umFLE9S4JqjLSSEK0N0tDFHCzDP6+KnhCftrZ3xw=";
              };
              buildInputs = with super; [ pbr six cryptography dateutil ];
              doCheck = false;
            };
            kvmd = super.buildPythonPackage rec {
              # https://github.com/pikvm/kvmd/blob/master/PKGBUILD
              # systemDeps are the external non-python dependencies. pythonDeps
              # are the Python dependencies. Neither are a valid argument for
              # buildPythonPackage, I'm just making it up so I can concatenate
              # them, to distinguish them from eachother, so it's easier to
              # read and reason about.
              # NOTES:
              # - I can't get teserract working
              # - These packages from the PKGBUILD are of interest, as I may not be supplying them properly.
              #   - "janus-gateway-pikvm>=0.11.2-7"
              #   - "raspberrypi-io-access>=0.5"
              propagatedBuildInputs = pythonDeps ++ systemDeps;
              systemDeps = with prev; [
                libgpiod
                freetype
                v4l-utils
                nginxMainline
                openssl
                platformio
                avrdude # this was avrdude-svn in the PKGBUILD, which might be different
                gnumake # why do we need make?
                gnupatch # May be unnecessary since patch should be included in the stdenv
                iptables
                iproute2
                dnsmasq
                ipmitool
                janus-gateway # We probably need the PiKVM custom janus-gateway
                ustreamer # This is coming from nixpkgs, but I probably want to use my own Flake
                zstd
                # dhclient # Probably given by networking.wireless.enable = true;
                # netctl # not packaged on Nix
                dos2unix
                parted
                e2fsprogs
                openssh
                wpa_supplicant
              ];
              pythonDeps = with self; [
                pyyaml
                aiohttp
                aiofiles
                passlib
                python-periphery
                pyserial
                spidev
                setproctitle
                psutil
                netifaces
                systemd
                dbus-python
                pygments
                pyghmi
                pam
                pillow
                xlib
                pam
              ];
              name = "kvmd";
              src = ./.;
              doCheck = false;
            };
          };
        };
      };

      # Provide some binary packages for selected system types.
      packages = forAllSystems (system:
        {
          inherit (nixpkgsFor.${system}) python39Packages;
        });

      # The default package for 'nix build'. This makes sense if the
      # flake provides only one package or there is a clear "main"
      # package.
      defaultPackage = forAllSystems (system: self.packages.${system}.python39Packages.kvmd);
    };
}
