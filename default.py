import sys
from resources.lib.tools import *

if __name__ == '__main__':
    try:
        p = sys.argv[1]
        if p.lower() == 'poweroff':
            setProperty('poweroff', True)
        else:
            notify(addonname, loc(30029))
    except IndexError:
        log('no parameter provided, exiting')
        xbmcgui.Dialog().ok(addonname, loc(30002).format(addonname))
