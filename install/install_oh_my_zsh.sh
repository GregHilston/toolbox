sh -c "KEEP_ZSHRC=yes $(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"

printf "⚠️  There may be above errors that would be caused by running toolbox Makefile more than once and can be safely ignored..."

# required if we want to rerun makefile, the above script fails. I want to avoid that
exit 0
