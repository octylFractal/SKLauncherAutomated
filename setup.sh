#!/usr/bin/env bash
pip_major=$(pip --version | grep -Eow 'python \d' | grep -Eow '\d')
command -v "pip3" > /dev/null 2>&1
no_pip3=$? # "0" -ne "$no_pip3" -> pip3 is there
if [[ "3" -ne "$pip_major" ]] && [[ "0" -ne "$no_pip3" ]]; then
    echo "Must have python 3 avalible via pip or pip3"
    exit 1
fi
if [[ "0" -ne "$no_pip3" ]]; then
    # no pip3, must be pip
    pip_cmd=pip
else
    pip_cmd=pip3
fi
"$pip_cmd" install sh easygui
