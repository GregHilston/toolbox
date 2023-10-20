## What's in it?

```
├── Dockerfile                              # Dockerfile defining a barebones system that one can try out this Toolbox in.
├── docker-build.sh                         # Command to build our Docker image.
├── docker-run.sh                           # Command to start a Docker container of our Docker image.
```

### To Build Image From `Dockerfile`

./docker/docker-build.sh

### To Run A Fresh Temporary Container and Shell Exec Into It

`$ ./docker/docker-run.sh`

_Note: This may require you to slightly modify the ./install.sh script to not check if the script was ran as sudo, as our container runs as root._
