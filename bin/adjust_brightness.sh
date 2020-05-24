CONNECTED_DISPLAY=$(xrandr -q | grep " connected" | awk '{print $1;}')
xrandr --output $CONNECTED_DISPLAY --brightness $1 
