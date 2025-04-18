service.rpm
===========

PVR 'Recording- & Power Manager NG²' for Kodi. This addon turns your Kodi on a Linux installation (pure Linux, Open-/LibreELEC) 
into a full featured video recorder (TV server and TV card required).

This addon handles power management for current active recordings and wakeup procedures for future schedules using the JSON-RPC-Interface of Kodi. The addon starts and shut down the HTPC if a recording is scheduled.

The new server mode allows the use of a Kodi installation as a pure recording and media server. The server is woken e.g. via WOL and makes its resources available until no more process, network or recording tasks are active. After that the system shuts down. If the user is cancelling the shut down process, the addon initiate a new idle time process. A defined time frame can also be used to extend the idle time until shutdown. 

The addon also starts the system periodically on a user defined cycle and time for e.g. EPG-updates if there is a longer 
inactivity time of the system or user. To collect the individual EPG data the script "epggrab_ext.sh" can be adapted to your needs.


Some installation notes
-----------------------
1.  THIS ADDON WORKS ONLY ON x86 BASED HARDWARE AS IT WRITES WAKEUP INFORMATIONS INTO THE HARDWARE (BIOS) RTC. IT DOESN'T WORK 
    ON AML NOR ARM BASED HARDWARE (ANDROID BOXES, RASPBERRY OR SIMILAR HARDWARE)
2.	YOU KNOW WHAT A TERMINAL CONSOLE IS AND YOU ARE ABLE TO USE IT.
3.	THIS ADDON USE ACPI-WAKEUP OVER RTC. YOUR MAINBOARD MUST SUPPORT THIS PROPERLY. NOTE THAT IN YOUR APM-SETTINGS OF 
    YOUR BOARD THE RTC WAKEUP SHOULD BE SET TO ‘by OS’ OR ‘disabled’. YOU CAN ALSO USE A SPECIAL USB REMOTE CONTROLLER 'Y.A.R.D.2'. 
    IF THIS IS CHOOSEN, THE RTC OF Y.A.R.D.2 IS USED. USEFULL FOR BOARDS WITHOUT RTC (RASPBERRY & CO.)
4.	PURE LINUX: THIS README USES ```kodi``` AS THE DEFAULT USER. IF KODI IS RUNNING WITH A DIFFERENT USERNAME, CHANGE ALL 
      OCCURENCES OF ```/home/kodi/``` TO ```/home/yourusername/``` IN YOUR PATHNAMES/NAMES.

Installation
------------

1.	Install this Addon from ZIP or from Repository

2.	If You are using OpenElec/LibreElec, the following step isn’t necessary. Skip to step 3. All others: As the shellscript ‘shutdown.sh’ is a wrapper to poweroff the system, it needs root privileges to run properly. We make it possible that ‘shutdown.sh’ runs under root/sudo privileges without needing to type in a password:


      sudo visudo
    
   add at the end of the file:
        
      Cmnd_Alias PVR_CMDS = /home/kodi/.kodi/addons/service.rpm/resources/lib/shutdown.sh
      kodi ALL=NOPASSWD: PVR_CMDS
    
   Store your changes (CTRL+O, CTRL+X)

3. Change your remote.xml to point the addon when "Power" on remote is pressed. If you don't have a remote control you can also define a special key on your keyboard as power button (here as example F12).

        
   Create a remote.xml if it doesn't exists:
    
      nano $HOME/.kodi/userdata/keymaps/remote.xml
    
   and copy/paste following code into the editor: 
    
            <keymap>
                <global>
                    <!-- This is the keyboard section -->
                    <keyboard>
                        <f12>RunScript(service.rpm,poweroff)</f12>
                    </keyboard>
                    <!-- This is the remote section -->
                    <remote>
                        <power>RunScript(service.rpm,poweroff)</power>
                    </remote>
                </global>
            </keymap>

4.	Store (CTRL+O, CTRL+X), restart Kodi and enjoy!


Y.A.R.D.2
---------

You have to make sure that your system knows the path to the yard2wakeup executable. Insert this line into the .profile file in your user folder:

    nano $HOME/.profile
    
and add

     PATH="$PATH:$HOME/yard2
     
In this case $HOME/yard2 points to the installation folder of yard2wakeup. On *Elec systems this could be /storage/yard2


ADDITIONAL FOR EXPERTS
----------------------

If you want to add a hook to the shutdown menu of kodi (this changes the behaviour of the power button), edit the ‘DialogButtonMenu.xml’ 
(or similar) in the xml part of the skin addon and look for a xml tag like (note the &lt;onclick&gt;Powerdown()&lt;/onclick&gt; inside here):

        <item>
            <label>$LOCALIZE[13016]</label>
            <onclick>Powerdown()</onclick>
            <visible>System.CanPowerDown</visible>
        </item>

and change this to:

        <item>
            <label>$LOCALIZE[13016]</label>
            <onclick>Powerdown()</onclick>
            <visible>System.CanPowerDown + !System.HasAddon(service.rpm)</visible>
        </item>
        <item>
            <label>$LOCALIZE[13016]</label>
            <onclick>RunScript(service.rpm,poweroff)</onclick>
            <visible>System.CanPowerDown + System.HasAddon(service.rpm)</visible>
        </item>

Don’t forget to store. Remember that you have to repeat this when the skin has updated. The skin "Estuary Mod V2" has this 
already implemented.

Please send Comments and Bugreports to birger.jesch@gmail.com

HINT: If your OS is CoreELEC/LibreELEC you have to turn off ‘Shutdown requires admin privileges’ as CoreELEC/LibreELEC doesn’t need sudo! 
This should be done automatically by the addon in most cases.

History
-------
- 3.2.0+matrix 17.04.2025: observing activity of Kodi audio player
- 3.1.0+matrix.1 04.04.2025: extend idle time frame in user mode up to 4 hrs
- 3.1.0+matrix 28.03.2025: komplete rewrite of the addon
