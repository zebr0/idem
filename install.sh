#!/bin/sh -e
sudo wget https://raw.githubusercontent.com/mazerty/idem/master/idem.py -O /usr/local/bin/idem.py
sudo wget https://raw.githubusercontent.com/mazerty/idem/master/template.py -O /usr/local/bin/template.py
sudo chmod +x /usr/local/bin/*.py
