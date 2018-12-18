# Firetron

*experimental, work in progress, do not use*

Create standalone desktop apps that use Firefox as a runtime.
Web browsers provide a stable and rich application environment. This
has made Electron a popular tool for building desktop applications.
Firetron is similar to Electron, but does is based on Firefox, making
it a more lightweight alternative. Further, apps created with Firetron
can make use of the Firefox that a user has installed on the system.
Therefore, frozen apps can be as small as 10 MB.

How it works (more or less):

* PyInstaller is used to freeze a launcher and optionally a server script.
* The result is bundled with a XUL application definition.
* The launcher detects the location of Firefox (on the system, or in the same bundle)
  and runs it with the `--app` argument pointing to the XUL application.

What kinds of apps can you create:

* Apps that simply display a website (but have their own window with icon etc.).
* Apps defined by static html/js/css assets.
* Apps using a server process.
* There is no NodeJS (which is positive thing, IMO).
