import os
import sys
import time
import shutil


def get_firefox_exe():
    """ Get the location of the Firefox executable on the system.
    Raise an error if not found.
    """
    # todo: Return user-specified version? e.g. when multiple are installer and one is corrupt
    
    paths = []
    
    # Look local to the executable
    localdir = os.path.join(os.path.dirname(sys.executable), "ff")
    if os.path.isdir(localdir):
        paths.append(os.path.join(localdir, os.path.basename(sys.executable)))
        paths.append(os.path.join(localdir, "firefox" + ".exe" * sys.platform.startswith("win")))
    
    # Collect possible locations
    if sys.platform.startswith('win'):
        for basepath in ('C:\\Program Files\\', 'C:\\Program Files (x86)\\'):
            paths.append(basepath + 'Mozilla Firefox\\firefox.exe')
            paths.append(basepath + 'Mozilla\\Firefox\\firefox.exe')
            paths.append(basepath + 'Firefox\\firefox.exe')
    elif sys.platform.startswith('linux'):
        paths.append('/usr/lib/firefox/firefox')
        paths.append('/usr/lib64/firefox/firefox')
        paths.append('/usr/lib/iceweasel/iceweasel')
        paths.append('/usr/lib64/iceweasel/iceweasel')
    elif sys.platform.startswith('darwin'):
        osx_user_apps = os.path.expanduser('~/Applications')
        osx_root_apps = '/Applications'
        paths.append(os.path.join(osx_user_apps, 'Firefox.app/Contents/MacOS/firefox'))
        paths.append(os.path.join(osx_root_apps, 'Firefox.app/Contents/MacOS/firefox'))
        if not any([os.path.isfile(path) for path in paths]):
            # Try harder - use app-id to get the .app path
            try:
                osx_search_arg='kMDItemCFBundleIdentifier==org.mozilla.firefox'
                basepath = subprocess.check_output(['mdfind', osx_search_arg])
                basepath = basepath.rstrip()
                if basepath:
                    paths.append(os.path.join(basepath, 'Contents/MacOS/firefox'))
            except (OSError, subprocess.CalledProcessError):
                pass

    # Try location until we find one that exists
    for path in paths:
        if os.path.isfile(path):
            return path
    
    # Getting desperate ...
    for path in os.getenv('PATH', '').split(os.pathsep):
        if 'firefox' in path.lower() or 'moz' in path.lower():
            for name in ('firefox.exe', 'firefox', 'iceweasel'):
                if os.path.isfile(os.path.join(path, name)):
                    return os.path.join(path, name)
    
    m = "Cannot find Firefox."
    m += "Install Mozilla Firefox from http://firefox.com"
    if sys.platform.startswith('linux'):
        m += ', or use your package manager.'
    raise RuntimeError(m)


def get_firefox_exe_version(exe):
    
    # Get raw version string (as bytes)
    if sys.platform.startswith('win'):
        if not os.path.isfile(exe):
            return
        # https://stackoverflow.com/a/4644565/2271927
        version = subprocess.check_output([exe, '--version', '|', 'more'])
        # version = subprocess.check_output(['wmic', 'datafile', 'where',
        #                                    'name=%r' % exe,
        #                                    'get', 'Version', '/value'])
    else:
        version = subprocess.check_output([exe, '--version'])
    
    # Clean up
    parts = version.decode(errors='ignore').strip().replace('=', ' ').split(' ')
    for part in parts:
        if part and part[0].isnumeric():
            return part


def copy_firefox_runtime(dir1, dir2, altname='xulrunner'):
    """ Copy the firefox/xulrunner runtime to a new folder, in which
    we rename the firefox exe to xulrunner. This thus creates a xul
    runtime in a location where we have write access. Used to be able
    to set the process name on Windows, and maybe used to distribute
    apps *with* the runtime.
    """
    t0 = time.time()
    # Get extension
    ext = '.exe' if sys.platform.startswith('win') else ''
    # On Rasberry Pi, the xul runtime is in a (linked) subdir
    if os.path.isdir(os.path.join(dir1, 'xulrunner')):
        dir1 = os.path.join(dir1, 'xulrunner')
    # Clear
    if os.path.isdir(dir2):
        shutil.rmtree(dir2)
    os.mkdir(dir2)
    try:
        # Copy all files except dirs
        for fname in os.listdir(dir1):
            filename1 = os.path.join(dir1, fname)
            filename2 = os.path.join(dir2, fname)
            if os.path.isfile(filename1):
                shutil.copy2(filename1, filename2)
        # Copy firefox exe -> xulrunner
        for exe_name in ('firefox', 'iceweasel', 'xulrunner', 'firefox'):
            exe = os.path.join(dir1, exe_name + ext)
            if os.path.isfile(exe):
                break
        shutil.copy2(exe, os.path.join(dir2, altname + ext))
        print('Copied firefox in %1.1f s' % (time.time()-t0))
    except Exception:
        # Clean up
        shutil.rmtree(dir2)
        raise