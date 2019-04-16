# -*- coding: utf-8 -*-
import sys
import os
import platform

import win32api
import win32con
import win32ts
import win32console
import pywintypes


def msgbox(msg, title='提示', warning=False, question=False, **kw):
    if 'icon' in kw:
        icon = kw['icon']
    else:
        if warning:
            icon = win32con.MB_ICONWARNING
        elif question:
            icon = win32con.MB_ICONQUESTION | win32con.MB_YESNO
        else:
            icon = win32con.MB_ICONINFORMATION
    if 'hwnd' in kw:
        hwnd = kw['hwnd']
    else:
        hwnd = 0
    if question:
        return win32api.MessageBox(hwnd, msg, title, icon) == win32con.IDYES
    else:
        win32api.MessageBox(hwnd, msg, title, icon)


def wts_msgbox(msg, title='提示', style=0, timeout=0, wait=False):
    # 这个函数支持在服务程序里弹出对话框
    sid = win32ts.WTSGetActiveConsoleSessionId()
    if sid != 0xffffffff:
        ret = win32ts.WTSSendMessage(win32ts.WTS_CURRENT_SERVER_HANDLE,
                                     sid, title, msg, style, timeout, wait)
        return ret


def runas_admin(exefile, param, workdir, showcmd=None):
    if showcmd is None:
        showcmd = win32con.SW_SHOWDEFAULT
    if platform.version() >= '6.0':  # Vista
        # pywintypes.error: (5, 'ShellExecute', '拒绝访问。')
        try:
            ret = win32api.ShellExecute(0, 'runas', exefile, param, workdir, showcmd)
        except pywintypes.error:  # @UndefinedVariable
            ret = -1
    else:
        try:
            ret = win32api.ShellExecute(0, None, exefile, param, workdir, showcmd)
        except pywintypes.error:  # @UndefinedVariable
            ret = -1
    return ret > 32


def getconsolehwnd():
    return win32console.GetConsoleWindow()


def redirectSystemStreamsIfNecessary(stdout=None, stderr=None):
    # Python programs running as Windows NT services must not send output to
    # the default sys.stdout or sys.stderr streams, because those streams are
    # not fully functional in the NT service execution environment.  Sending
    # output to them will eventually (but not immediately) cause an IOError
    # ("Bad file descriptor"), which can be quite mystifying to the
    # uninitiated.  This problem can be overcome by replacing the default
    # system streams with a stream that discards any data passed to it (like
    # redirection to /dev/null on Unix).
    #
    # However, the pywin32 service framework supports a debug mode, under which
    # the streams are fully functional and should not be redirected.
    shouldRedirect = True
    try:
        import servicemanager
    except ImportError:
        # If we can't even 'import servicemanager', we're obviously not running
        # as a service, so the streams shouldn't be redirected.
        shouldRedirect = False
    else:
        # Unlike previous builds, pywin32 builds >= 200 allow the
        # servicemanager module to be imported even in a program that isn't
        # running as a service.  In such a situation, it would not be desirable
        # to redirect the system streams.
        #
        # However, it was not until pywin32 build 203 that a 'RunningAsService'
        # predicate was added to allow client code to determine whether it's
        # running as a service.
        #
        # This program logic redirects only when necessary if using any build
        # of pywin32 except 200-202.  With 200-202, the redirection is a bit
        # more conservative than is strictly necessary.
        if servicemanager.Debugging() or \
                (hasattr(servicemanager, 'RunningAsService') and not
                servicemanager.RunningAsService()):
            shouldRedirect = False

    if shouldRedirect:
        if not stdout:
            stdout = open('nul', 'w')
        sys.stdout = stdout
        if not stderr:
            stderr = open('nul', 'w')
        sys.stderr = stderr
    return shouldRedirect


def get_fileversion(filename):
    info = win32api.GetFileVersionInfo(filename, os.sep)
    ms = info['FileVersionMS']
    ls = info['FileVersionLS']
    version = '%d.%d.%d.%d' % (win32api.HIWORD(ms), win32api.LOWORD(ms), win32api.HIWORD(ls), win32api.LOWORD(ls))
    return version


def get_fileversioninfo(filename):
    """
    Read all properties of the given file return them as a dictionary.
    """
    propNames = ('Comments', 'InternalName', 'ProductName',
                 'CompanyName', 'LegalCopyright', 'ProductVersion',
                 'FileDescription', 'LegalTrademarks', 'PrivateBuild',
                 'FileVersion', 'OriginalFilename', 'SpecialBuild')

    props = {'FixedFileInfo': None, 'StringFileInfo': None, 'FileVersion': None}

    # backslash as parm returns dictionary of numeric info corresponding to VS_FIXEDFILEINFO struc
    fixedInfo = win32api.GetFileVersionInfo(filename, '\\')
    props['FixedFileInfo'] = fixedInfo
    props['FileVersion'] = '%d.%d.%d.%d' % (fixedInfo['FileVersionMS'] / 65536,
                                            fixedInfo['FileVersionMS'] % 65536, fixedInfo['FileVersionLS'] / 65536,
                                            fixedInfo['FileVersionLS'] % 65536)

    # \VarFileInfo\Translation returns list of available (language, codepage)
    # pairs that can be used to retreive string info. We are using only the first pair.
    lang, codepage = win32api.GetFileVersionInfo(filename, '\\VarFileInfo\\Translation')[0]

    # any other must be of the form \StringfileInfo\%04X%04X\parm_name, middle
    # two are language/codepage pair returned from above

    strInfo = {}
    for propName in propNames:
        strInfoPath = u'\\StringFileInfo\\%04X%04X\\%s' % (lang, codepage, propName)
        strInfo[propName] = win32api.GetFileVersionInfo(filename, strInfoPath)

    props['StringFileInfo'] = strInfo
    return props
