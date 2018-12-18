"""
Code to launch an app live from the Python interpreter, for use during
development.
"""


def launch_app(self, url):
    
    # Get dir to store app definition
    app_path = create_temp_app_dir('firefox')
    id = op.basename(app_path).split('_', 1)[1].replace('~', '_')
    
    # Set size and position
    # Maybe interesting window features: alwaysRaised
    windowfeatures = 'resizable=1,minimizable=1,dialog=0,'
    if self._windowmode == 'normal':
        windowfeatures += 'width=%i,height=%i' % self._size
        if self._pos:
            windowfeatures += ',left=%i,top=%i' % self._pos

    # Create files for app
    # self._create_xul_app(app_path, id, url, windowfeatures)

    # Get executable for xul runtime (may be None)
    ff_exe = self.get_exe()
    if not ff_exe:
        raise RuntimeError('Firefox is not available on this system.')
    elif not op.isfile(ff_exe):
        # We have no way to wrap things up in a custom app
        exe = ff_exe
    else:
        # We make sure the runtime is "installed" and mangle the name
        xul_exe = op.join(self.get_runtime_dir(), 'xulrunner')
        xul_exe += '.exe' * sys.platform.startswith('win')
        exe = self._get_app_exe(xul_exe, app_path)
    
    # Prepare profile dir for Xul to let -profile dir point to.
    # This dir is unique for each instance of the app, but because it is
    # inside the app_path, it gets automatically cleaned up.
    profile_dir = op.join(app_path, 'stub_profile')
    if not op.isdir(profile_dir):
        os.mkdir(profile_dir)
    
    # Launch
    cmd = [exe, '-app', op.join(app_path, 'application.ini'),
            '-profile', profile_dir]
    self._start_subprocess(cmd)
