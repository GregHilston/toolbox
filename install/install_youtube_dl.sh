# At the time of writing this youtube-dl in apt was out of date, back from 2020
# Using the instllation on the main website https://ytdl-org.github.io/youtube-dl/download.html had problems with which python version it was using
# `$ sudo curl -L https://yt-dl.org/downloads/latest/youtube-dl -o /usr/local/bin/youtube-dl`
# `$ sudo chmod a+rx /usr/local/bin/youtube-dl`
# all that worked was the binary in snap
sudo snap install youtube-dl
