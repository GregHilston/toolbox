# Ansible README

## To add a new device

- add to `/etc/hosts`, then `inventory.cfg`
- 
- run from toolbox/ansible folder `$ ansible-playbook playbooks/install_sudo_and_group.yml playbooks/install_ansible_user.yml --limit <host> -u [user name already on system]`
  - For password auth, add `-k`
  - For sudo password prompt, add `-K`

## To update apt and upgrade all packages

- run `$ ansible-playbook playbooks/update_upgrade_apt.yml --limit <host name>`