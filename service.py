import time
import xbmcvfs
import socket
import threading
import stat

osv = release()
if osv.get('ARCH', 'not detected') not in ['i386', 'i686', 'x86_64']:
    messageOk(loc(30045), loc(30046))
    query = {'method': 'Addons.SetAddonEnabled', 'params': {'addonid': addonid, 'enabled': False}}
    if jsonrpc(query) == 'OK':
        log('Addon disabled due hardware incompatibility: %s' % osv.get('ARCH', 'not detected'), xbmc.LOGINFO)
    else:
        log('Could not disable Addon (%s not compatible)' % osv.get('ARCH', 'not detected'), xbmc.LOGERROR)
    exit(0)

SHUTDOWN_CMD = xbmcvfs.translatePath(os.path.join(addonpath, 'resources', 'lib', 'shutdown.sh'))
EXTGRABBER = xbmcvfs.translatePath(os.path.join(addonpath, 'resources', 'lib', 'epggrab_ext.sh'))

# set permissions for SHUTDOWN_CMD/EXTGRABBER, required after installation or update

_sts = os.stat(SHUTDOWN_CMD).st_mode
_stg = os.stat(EXTGRABBER).st_mode
if not (_sts & stat.S_IXOTH): os.chmod(SHUTDOWN_CMD, _sts | stat.S_IXOTH)
if not (_stg & stat.S_IXOTH): os.chmod(EXTGRABBER, _stg | stat.S_IXOTH)

Mon = Monitor()
Mon.settings = addon_settings
Mon.getAddonSettings()

setProperty('poweroff', 'False')
setProperty('observe', 'False')
setProperty('epg_exec_done', 'False')

osv = release()
log('OS ID is {} {}'.format(osv['ID'], osv['VERSION_ID']), xbmc.LOGINFO)
if osv['ID'].lower() in ['libreelec', 'openelec'] and Mon.setting['sudo']:
    Mon.setSetting('sudo', False)
    log('Reset wrong setting \'sudo\' to False')

Mon.settingsChanged = False
Mon.logSettings()


class EpgThread(threading.Thread):
    def __init__(self, mode=None):
        threading.Thread.__init__(self)
        self.mode = mode

    def run(self):
        initialize = time.time()
        if self.mode == 0:
            xbmc.sleep(Mon.setting['epgtimer_duration'] * 60000)
        elif self.mode == 1:
            runExtEpg(Mon.setting['epg_script'], Mon.setting['epg_socket'])
        elif self.mode == 2:
            copy2Socket(Mon.setting['epg_file'], Mon.setting['epg_socket'])
        else:
            log('wrong or missing threading parameter: {}'.format(self.mode))
        setProperty('epg_exec_done', 'True')
        log('EPG thread took {} secs'.format(int(time.time() - initialize)))


def countDown(flags):
    if Mon.setting['server_mode'] or flags & isATF:
        pbar = ProgressBar(loc(30030), loc(30011).format(addonname), reverse=True)
    else:
        pbar = ProgressBar(loc(30010), loc(30011).format(addonname),
                           duration=Mon.setting['notification_time'], steps=Mon.setting['notification_time'],
                           reverse=True)
    return not pbar.show_progress()

def copy2Socket(source, tvhsocket):
    if xbmcvfs.exists(source) and xbmcvfs.exists(tvhsocket):
        s = xbmcvfs.File(source)
        transfer = True
        chunks = 0
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.connect(tvhsocket)
            while transfer:
                chunk = s.readBytes(4096)
                if not chunk:
                    log('{} chunks transmitted'.format(chunks))
                    break
                sock.send(chunk)
                chunks += 1
        except socket.error as e:
            log('couldn\'t write to socket: {}'.format(e), xbmc.LOGERROR)
        finally:
            sock.close()
            s.close()
            return True
    else:
        log('couldn\'t copy EPG XML source to socket', xbmc.LOGERROR)
        log('Source file or socket doesn\'t exist. Check your settings', xbmc.LOGERROR)
    return False

def runExtEpg(script, tvhsocket):
    if osv['PLATFORM'] == 'Linux' and os.path.isfile(script) and os.path.isfile(tvhsocket):
        try:
            _comm = subprocess.Popen('%s %s' % (script, tvhsocket),
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     shell=True, universal_newlines=True)
            while _comm.poll() is None:
                xbmc.sleep(1000)
        except subprocess.SubprocessError as e:
            log('Could not start external script: {}'.format(e), xbmc.LOGERROR)

def getPvrStatus():

    Mon.checkPvrPresence(quiet=True)
    if not Mon.hasPVR: return isUSR

    # check for recordings and timers
    Mon.nextTimer = 0
    query = {'method': 'PVR.GetTimers', 'params': {'properties': ['starttime', 'startmargin', 'istimerrule', 'state']}}
    response = jsonrpc(query)
    if response and response.get('timers', False):
        for timer in response.get('timers'):
            if timer['istimerrule'] or timer['state'] == 'disabled':
                continue
            if timer['state'] == 'recording':
                return isREC
            elif time.mktime(time.strptime(timer['starttime'], JSON_TIME_FORMAT)) - \
                    Mon.setting['margin_start'] - \
                    Mon.setting['margin_stop'] - \
                    Mon.setting['notification_time'] - \
                    (timer['startmargin'] * 60) + TIME_OFFSET < int(time.time()):
                return isREC
            else:
                Mon.nextTimer = int(time.mktime(time.strptime(timer['starttime'], JSON_TIME_FORMAT)) -
                                    Mon.setting['margin_start'] - (timer['startmargin'] * 60) + TIME_OFFSET)
                break
    return isUSR

def getEpgStatus():

    # Check for EPG update
    Mon.nextEPG = 0
    if Mon.setting['epgtimer_interval'] > 0:
        __next = time.mktime(time.localtime()) + (int(time.strftime('%j')) % Mon.setting['epgtimer_interval']) * 86400
        __n = datetime.fromtimestamp(__next).replace(hour=Mon.setting['epgtimer_time'],
                                                     minute=0, second=0, microsecond=0)
        if not str2bool(getProperty('epg_exec_done')):
            if datetime.timestamp(__n) - Mon.setting['margin_start'] - \
                    Mon.setting['margin_stop'] < \
                    time.mktime(time.localtime()) < datetime.timestamp(__n) + \
                    (Mon.setting['epgtimer_duration'] * 60):
                return isEPG
        Mon.nextEPG = int(datetime.timestamp(__n) - Mon.setting['margin_start'])
        if Mon.nextEPG + Mon.setting['epgtimer_duration'] * 60 < time.mktime(time.localtime()):
            Mon.nextEPG += int(Mon.setting['epgtimer_interval'] * 86400)
    return isUSR

def getProcessStatus():

    # check for running processes
    if Mon.setting['check_postprocesses']:
        processes = Mon.setting['monitored_processes'].split(',')

        for proc in processes:
            if getProcessPID(proc.strip()):
                return isPRG
    return isUSR

def getNetworkStatus():

    # check for active network connection(s)
    if Mon.setting['check_network']:
        ports = Mon.setting['monitored_ports'].split(',')

        for port in ports:
            if getPorts(port.strip()):
                return isNET
    return isUSR

def getTimeFrameStatus():

    # check for active time frame
    if Mon.setting['main_activity'] and Mon.setting['server_mode']:
        if Mon.setting['main_activity_start'] * 3600 < \
                (datetime.now() - datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)).seconds < \
                Mon.setting['main_activity_stop'] * 3600:
            return isATF
    return isUSR

def getPwrStatus():
    if Mon.waitForShutdown:
        return isPWR
    return isUSR

def getStatusFlags(flags):

    _flags = isUSR | getPvrStatus() | getEpgStatus() | getProcessStatus() | getNetworkStatus() | \
             getTimeFrameStatus() | getPwrStatus()
    if _flags ^ flags:
        log('Status changed: {:06b} (PWR/ATF/NET/PRG/REC/EPG)'.format(_flags), xbmc.LOGINFO)
    return _flags

def checkShutdownProperty():
    # check for user activity and power off required by user
    if getProperty('poweroff'):
        Mon.waitForShutdown = True
        setProperty('poweroff', 'False')
        setProperty('observe', 'False')
        log('Shutdown required by user')
        return True
    return False

def service():

    flags = getStatusFlags(isUSR)
    # setProperty('observe', False)

    # Mon.waitForShutdown = True if Mon.setting['server_mode'] else False

    # This is the initial startup after boot, if flags isREC | isEPG are set, a recording
    # or EPG update is immediately started. set 'poweroff' to true, also set 'observe' to true
    # avoiding notifications on initial startup

    if flags & (isREC | isEPG):
        setProperty('poweroff', 'True')
        setProperty('observe', 'True')

    # start EPG grabber threads

    if flags & isEPG:
        thread = EpgThread(Mon.setting['epg_mode'])
        thread.start()

    # ::MAIN LOOP::

    idle = 0
    cycle = Mon.setting['sm_idletime'] if Mon.setting['server_mode'] and not Mon.setting['main_activity'] and not (flags & isATF) else Mon.setting['um_idletime']

    while not Mon.abortRequested():

        flags = getStatusFlags(flags)

        while idle < cycle:
            if Mon.abortRequested():
                break

            if Mon.settingsChanged:
                Mon.getAddonSettings()
                Mon.settingsChanged = False

                # define max idle time depending on addon mode
                cycle = Mon.setting['sm_idletime'] if Mon.setting['server_mode'] and not Mon.setting['main_activity'] and not (flags & isATF) else Mon.setting['um_idletime']

            idle = xbmc.getGlobalIdleTime()
            # log('System is {} secs idle'.format(idle))
            xbmc.sleep(2000)

            # check for user activity and power off required by user
            if checkShutdownProperty(): break

            if xbmc.getGlobalIdleTime() < idle:
                log('User activity detected, reset idle time')
                Mon.waitForShutdown = False
                setProperty('observe', 'False')

        Mon.waitForShutdown = True

        flags = getStatusFlags(flags)
        if flags & isPWR:

            if not flags & (isREC | isEPG | isPRG | isNET):

                if not countDown(flags):
                    Mon.waitForShutdown = False
                    setProperty('poweroff', 'False')
                    idle = 0
                    continue

                # power off
                _t = 0
                if Mon.calcNextEvent():
                    _m, _t = Mon.calcNextEvent()
                    _ft = datetime.strftime(datetime.fromtimestamp(_t), LOCAL_TIME_FORMAT)
                    log('next schedule: {}'.format(_ft))
                    if Mon.setting['show_next_sched'] and not Mon.setting['server_mode']:
                        notify(loc(30024), loc(_m).format(_ft))
                else:
                    log('no schedules')
                    if Mon.setting['show_next_sched'] and not Mon.setting['server_mode']:
                        notify(loc(30040), loc(30014))

                xbmc.sleep(5000)
                log('set RTC to {}'.format(_t))
                if osv['PLATFORM'] == 'Linux':
                    sudo = 'sudo ' if Mon.setting['sudo'] else ''
                    os.system('%s%s %s %s %s' % (sudo, SHUTDOWN_CMD, _t,
                                                 Mon.setting['shutdown_method'],
                                                 Mon.setting['shutdown_mode']))

                if Mon.setting['shutdown_method'] == 0 or osv['PLATFORM'] == 'Windows':
                    xbmc.shutdown()

            if not getProperty('observe'):
                if flags & isREC:
                    notify(loc(30015), loc(30020), icon=xbmcgui.NOTIFICATION_WARNING)  # Notify 'Recording in progress'
                elif flags & isEPG:
                    notify(loc(30015), loc(30021), icon=xbmcgui.NOTIFICATION_WARNING)  # Notify 'EPG-Update'
                elif flags & isPRG:
                    notify(loc(30015), loc(30022), icon=xbmcgui.NOTIFICATION_WARNING)  # Notify 'Postprocessing'
                elif flags & isNET:
                    notify(loc(30015), loc(30023), icon=xbmcgui.NOTIFICATION_WARNING)  # Notify 'Network active'
                elif flags & isATF:
                    notify(loc(30015), loc(30033), icon=xbmcgui.NOTIFICATION_WARNING)  # Notify 'Time Frame active'
                setProperty('observe', 'True')

        walker = 20

        while walker > 0:
            if checkShutdownProperty(): break
            elif xbmc.getGlobalIdleTime() < idle:
                idle = 0
                break

            xbmc.sleep(2000)
            walker -= 1


if __name__ == '__main__':
    service()
    log('Service finished', xbmc.LOGINFO)
