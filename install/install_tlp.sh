sudo add-apt-repository ppa:linrunner/tlp
sudo apt update
# last two packages for thinkpads x201 and t420
sudo apt install tlp tlp-rdw acpi-call-dkms tp-smapi-dkms -y
sudo tlp start
