#! /bin/sh

## Please place your command line for grabbing epg-data from external provider here
## Make sure all grabbers are configured properly and choose the appropriate socket
## of tvheadend!
##
## More information about XMLTV: http://wiki.xmltv.org/index.php/Main_Page
## XMLTV Project Page: http://sourceforge.net/projects/xmltv/files/
##
## Arguments: $1: path of PyEPG/XMLTV socket of tvheadend
##
## Provider: epgdata.com
# tv_grab_eu_epgdata --days=4 | nc -U "$1"

## Provider: Egon zappt (german)
# tv_grab_eu_egon --days=4 | nc -w 5 -U "$1"

## Please comment out the next 2 lines!
echo "This script use socket $1 and will sleep for 30 secs"
sleep 30
##
exit 0
