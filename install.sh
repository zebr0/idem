#!/bin/sh -e
wget https://raw.githubusercontent.com/mazerty/idem/master/idem.py -O /usr/local/bin/idem.py
wget https://raw.githubusercontent.com/mazerty/idem/master/template.py -O /usr/local/bin/template.py
chmod +x /usr/local/bin/*.py
