## What's in it?

```
├── Dockerfile                              # Dockerfile defining a barebones system that one can try out this Toolbox in.
├── docker-build.sh                         # Script to build our Docker image.
├── docker-run.sh                           # Script to start a Docker container of our Docker image.
```

### To Build Image From `Dockerfile`

./docker/docker-build.sh

### To Run A Fresh Temporary Container and Shell Exec Into It

`$ ./docker/docker-run.sh`

### To Run Toolbox In Docker

Here are the steps needed to run this tool in a standalone container:

1. Since we're in a barebones system, we'll have to bootstrap our necessary dependencies: `$ ./bootstrap.sh`
2. Source our bashrc file so we have ansible-playbook in our PATH: `$ source ~/.bashrc`
3. Run our installation script: `$ ./install.sh`