"""
Create a distributable app.
"""

import os
import sys
import shutil

from ._createxul import create_xul_app
from ._findff import copy_firefox_runtime, get_firefox_exe


def create_app(target_dir, name, app, title=None, icon=None, include_firefox=False):
    
    # We don't want want to include PyInstaller by default when *this* lib is frozen
    import importlib
    try:
        pyinstaller_run = importlib.import_module("PyInstaller.__main__").run
    except ImportError:
        raise ImportError("firetron.create_app needs PyInstaller (pip install pyinstaller)")
    
    # Start with a clean target directory
    print("===== Creating/cleaning target directory")
    if os.path.isdir(target_dir):
        shutil.rmtree(target_dir)
    os.mkdir(target_dir)
    
    # Determine what to run
    
    # Create the XUL application
    print("===== Creating XUL application")
    title = title or name
    id = name
    url = app  # todo: only when app is a string starting with http://
    windowfeatures = 'resizable=1,minimizable=1,dialog=0,'
    windowmode = "normal"  # 'normal', 'maximized', 'fullscreen', 'kiosk'
    create_xul_app(os.path.join(target_dir, "xul"), title, id, url, windowfeatures, windowmode, icon)
    
    print("===== Prepare for PyInstaller")
    
    # Copy launcher code
    print("Create launcher script")
    launcher_filename = os.path.join(target_dir, name + ".py")
    with open(launcher_filename, 'wb') as f:
        f.write(launcher_code.encode())
    
    # Determine icon file
    iconfile = None
    if icon is None:
        pass
    elif sys.platform.startswith("win"):
        iconfile = os.path.join(target_dir, 'icon.ico')
    elif sys.platform.startswith("darwin"):
        iconfile = os.path.join(target_dir, 'icon.icns')
    
    # Compose PyInstaller command
    cmd = [launcher_filename, "--windowed",
            "--distpath", target_dir,
            "--workpath", target_dir + "/build",
            "--specpath", target_dir,
            ]
    if iconfile:
        print("Writing icons")
        icon.write(iconfile)
        cmd += ["--icon", iconfile]
    
    # Call PyInstaller
    print("===== Running PyInstaller to create the executables")
    try:
        pyinstaller_run(cmd)
    except SystemExit:
        raise RuntimeError("FAIL")
    
    # Clean up after PyInstaller
    print("===== Cleaning up")
    for x in os.listdir(os.path.join(target_dir, name)):
        os.rename(os.path.join(target_dir, name, x), os.path.join(target_dir, x))
    for fname in (launcher_filename, launcher_filename[:-3] + ".spec", iconfile, None):
        if fname and os.path.isfile(os.path.join(target_dir, fname)):
            os.remove(os.path.join(target_dir, fname))
    for dname in ("build", name, "__pycache__", None):
        if dname and os.path.isdir(os.path.join(target_dir, dname)):
            shutil.rmtree(os.path.join(target_dir, dname))
    
    # Copy over firefox directory
    if include_firefox:
        print("===== Copying Firefox runtime")
        exe = get_firefox_exe()  # Raises RuntimeError if not found
        copy_firefox_runtime(os.path.dirname(exe), os.path.join(target_dir, "ff"), name)
        
    print("===== Done!")


launcher_code = """
import os
import sys
import tempfile

import dialite
import firetron

ffnotfound = '''
This app requires Firefox to run.
Could not locate Firefox executable!

Please install Firefox (e.g. from https://firefox.com)
'''.strip()

try:
    ffexe = firetron.get_firefox_exe()
except RuntimeError:
    dialite.warn("Firefox not found", ffnotfound)
    sys.exit(1)

if sys.platform.startswith("win"):
    exename = os.path.basename(sys.executable)[:-4]
    exedir = os.path.dirname(os.path.abspath(sys.executable))
    xul = os.path.join(exedir, "xul", "application.ini")
    
    # Create shortcut
    lnk_path = os.path.join(tempfile.gettempdir(), sys.executable[:-4] + ".lnk")
    firetron.create_lnk(lnk_path,
        target=ffexe,
        arguments='--app "' + xul + '"',
        work_dir=exedir, 
        comment="Run " + exename + " on the Firefox XUL runtime",
        icon=os.path.join(exedir, "xul", "chrome", "icons", "default", "W" + exename + ".ico"),
        run_mode="normal",
    )
    
    # Start new process (not a subprocess). By using the shortcut instead
    # of a direct call to FF, the app can be pinned to the taskbar.
    os.startfile(lnk_path)  # startfile is Windows-only
    #os.execl(ffexe, sys.executable, "--app", xul)

else:
    raise NotImplementedError()
"""
