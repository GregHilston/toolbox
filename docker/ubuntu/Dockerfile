FROM ubuntu:22.04

ARG USERNAME=toolbox
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Set configuration needed so Ansible installation will not ask us questions
# during installation. Based on:
# https://dev.to/setevoy/docker-configure-tzdata-and-timezone-during-build-21bk
ENV TZ=Europe/Kiev
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Create the non-root user
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    #
    # [Optional] Add sudo support. Omit if you don't need to install software after connecting.
    && apt-get update \
    && apt-get install -y sudo \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# [Optional] Set the default user. Omit if you want to keep the default as root.
USER $USERNAME

# Required to allow Flatpak to work in our Docker container. Learned about
# this approach here:
# https://github.com/flatpak/flatpak/issues/5076#issuecomment-1425841966
# which links to here:
# https://invent.kde.org/sysadmin/ci-images/-/merge_requests/99/diffs#9ecac16eff5bf2026941d65c5ab5fce22e080caf_19_20
ENV FLATPAK_SYSTEM_HELPER_ON_SESSION=foo

# keeps the container alive
CMD ["tail", "-f", "/dev/null"]
