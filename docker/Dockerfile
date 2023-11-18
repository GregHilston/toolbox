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

# keeps the container alive
CMD ["tail", "-f", "/dev/null"]