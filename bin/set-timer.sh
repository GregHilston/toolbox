settimer() {
    say --voice karen "timer started"
    sleep $(echo "$1 * 60" | bc)
    say --voice karen "timer done"
}
settimer $1
