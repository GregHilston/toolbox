settimer() {
    sleep $(echo "$1 * 60" | bc)
    say --voice karen "timer done"
}
settimer $1
