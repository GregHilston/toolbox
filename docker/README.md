# Docker

Before committing to using this toolbox, it would be wise to play around with it in an ephemeral environment. This allows one to explore how it works, and to more easily develop changes, without causing changes in your host operating system.

## What Is In This Directory?

```bash
├── Dockerfile                              # Dockerfile defining a barebones system that one can try out this Toolbox in.
├── docker-build.sh                         # Script to build our Docker image.
├── docker-run.sh                           # Script to start a Docker container of our Docker image.
```

## How To Build Image From `Dockerfile`

./docker/docker-build.sh

## How To Run A Fresh Temporary Container and Shell Exec Into It

`$ ./docker/docker-run.sh`

## How To Run Toolbox In Docker

Once you've ran the above `$ ./docker/docker-run.sh`, you'll have a shell inside the ephemeral container. Here are the following steps to install this repository in that environment:

1. Since we're in a barebones system, we'll have to bootstrap our necessary dependencies: `$ ./bootstrap.sh`
2. Source our `~/.bashrc` file so we have ansible-playbook in our PATH: `$ source ~/.bashrc`
3. Run our installation script: `$ ./install.sh`
