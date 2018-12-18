import os
import sys
import shutil

packagename = "firetron"


def create_xul_app(path, title, id, url, windowfeatures, windowmode="normal", icon=None):
    """ Create the files that determine the XUL app to launch.
    """
    
    assert windowmode in ('normal', 'maximized', 'fullscreen', 'kiosk')
    modemap = {'kiosk': 'fullscreen'}
    
    # Dict with all values that are injected in the file templates
    # The name must be unique to avoid all sort of oddities when launching
    # multiple runtimes (as we do in flexx.app tests). Note that we've had
    # problems with the profile dirs being spammed (NW did, now fixed).
    # Also see "Profile=" in APPLICATION_INI.
    D = dict(vendor=packagename + ' contributors',
                name=packagename + '_' + id,
                version='1.0',
                buildid='1',
                id='app_{}@{}.io'.format(id, packagename),
                windowid='W' + id,
                title=title,
                url=url,
                sizemode=modemap.get(windowmode,windowmode),
                windowfeatures=windowfeatures,
                profilename=packagename + "_profile",
                
                )
    
    # Fill in arguments in file contents
    manifest_link = 'manifest chrome/chrome.manifest'
    manifest = 'content {name} content/'.format(**D)
    application_ini = APPLICATION_INI.format(**D)
    main_xul = MAIN_XUL.format(**D)
    main_js = MAIN_JS  # No format (also problematic due to braces)
    prefs_js = PREFS_JS.format(**D)

    # Clear
    if os.path.isdir(path):
        shutil.rmtree(path)

    # Create directory structure
    for subdir in ('',
                    'chrome', 'chrome/content',
                    'chrome/icons', 'chrome/icons/default',
                    'defaults', 'defaults/preferences',
                    ):
        os.mkdir(os.path.join(path, subdir))

    # Create files
    for fname, text in [('chrome.manifest', manifest_link),
                        ('chrome/chrome.manifest', manifest),
                        ('application.ini', application_ini),
                        ('defaults/preferences/prefs.js', prefs_js),
                        ('chrome/content/main.js', main_js),
                        ('chrome/content/main.xul', main_xul),
                        ]:
        with open(os.path.join(path, fname), 'wb') as f:
            f.write(text.encode())

    # Icon - use Icon class to write a png (Unix) and an ico (Windows)
    if icon is not None:
        icon_name = os.path.join(path, 'chrome/icons/default/' + D['windowid'])
        icon.write(icon_name + '.ico')
        icon.write(icon_name + '.icns')
        icon.write(icon_name + '.png')


## ____________________ templates ____________________

# By putting templates here in-file, we can make this package zip-safe


APPLICATION_INI = """
[App]
Vendor={vendor}
Name={name}
Version={version}
BuildID={buildid}
ID={id}
Profile={profilename}

[Gecko]
MinVersion=1.8
MaxVersion=200.*
""".lstrip()


MAIN_XUL = """
<?xml version="1.0"?>
<?xml-stylesheet href="chrome://global/skin/" type="text/css"?>

<window
    xmlns="http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul"
    id="{windowid}"
    title="{title}"
    windowtype="thisapp:main"
    width="640"
    height="480"
    sizemode="{sizemode}"
    onclose="quit();"
    >
    <script type="application/javascript"
            src="chrome://{name}/content/main.js" />
    <!-- content or content-primary ? -->
    <browser src="{url}"
             id="content"
             type="content"
             flex="1"
             disablehistory="true" />
</window>

""".lstrip()


MAIN_JS = """
// https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XPCOM/Reference/Interface/nsIProcess

// create an nsIFile for the executable
var file = Components.classes["@mozilla.org/file/local;1"]
                     .createInstance(Components.interfaces.nsIFile);
file.initWithPath("c:\\\\pythons\\\\python37\\\\python.exe");

// Create an nsIProcess and run it
// Note that it is *not* a subprocess of this process; if *this* process
// terminates, the created process stays alive ...
var process = Components.classes["@mozilla.org/process/util;1"]
                        .createInstance(Components.interfaces.nsIProcess);
process.init(file);
var args = [];
process.runwAsync(args, args.length);  // This function also allows observing the process from quitting


// When *this* process exits ...
function quit() {
    if (process.isRunning) { process.kill(); }
}

""".lstrip()


PREFS_JS = """
// This tells xulrunner what xul file to use
pref("toolkit.defaultChromeURI", "chrome://{name}/content/main.xul");

// This line is needed to let window.open work
pref("browser.chromeURL", "chrome://{name}/content/main.xul");

// Set features - setting width, height, maximized, etc. here
pref("toolkit.defaultChromeFeatures", "{windowfeatures}");

// debugging prefs, disable these before you deploy your application!
pref("browser.dom.window.dump.enabled", false);
pref("javascript.options.showInConsole", false);
pref("javascript.options.strict", false);
pref("nglayout.debug.disable_xul_cache", false);
pref("nglayout.debug.disable_xul_fastload", false);
""".lstrip()
