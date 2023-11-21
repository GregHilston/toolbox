# This starts and shell execs a throw away container that will be deleted after
# stopped for clarity, all changes made outside of the volume'd in toolbox will
# be lost this is useful for testing out our toolbox.

# --privileged is added so that flatpaks can install in user namespaces. Read
# here for more information:
# https://discourse.flathub.org/t/error-running-flatpack-in-dockerfile/1636

docker run --privileged --rm -it --volume $(pwd):/toolbox --workdir /toolbox --entrypoint /bin/bash toolbox-ubuntu
