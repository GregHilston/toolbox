# this starts and shell execs a throw away container that will be deleted after stopped
# for clarity, all changes made outside of the volume'd in toolbox will be lost
# this is useful for testing out our toolbox
docker run --rm -it --volume $(pwd):/toolbox --workdir /toolbox --entrypoint /bin/bash toolbox 
