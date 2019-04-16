# -*- coding: gbk -*-
import sys
import os
import re
import time
import json
import pickle
import codecs
import locale
from functools import partial


def format_frame(s, linelen=0):
    if not linelen:
        result = ' '.join(['%.2X' % ord(a) for a in s])
    else:
        lines = []
        while s:
            para, s = s[:linelen], s[linelen:]
            line = ' '.join(['%.2X' % ord(a) for a in para])
            lines.append(line)
        result = '\n'.join(lines)
    return result


def isoformat_date(gmt=None):
    return time.strftime('%Y-%m-%d', time.localtime(gmt))


def isoformat_time(gmt=None):
    return time.strftime('%H:%M:%S', time.localtime(gmt))


def isoformat_datetime(gmt=None):
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(gmt))


def dhms(seconds):
    minutes = seconds / 60
    d = int(minutes / (24 * 60))
    h = int(minutes % (24 * 60) / 60)
    m = int(minutes % 60)
    s = ''
    if d:
        s += '%d天' % d
    if h:
        s += '%d小时' % h
    if m:
        s += '%d分钟' % m
    sec = seconds % 60
    if sec or not s:
        s += '%d秒' % sec
    return s


class SafeDumper(object):
    def __init__(self, filename):
        self.dumpfile = filename
        self.dumpfile_new = filename + '.1'

    def save(self, obj):
        fp = open(self.dumpfile_new, 'wb')
        pickle.dump(obj, fp, pickle.HIGHEST_PROTOCOL)
        fp.close()
        if os.path.isfile(self.dumpfile):
            os.remove(self.dumpfile)
        os.rename(self.dumpfile_new, self.dumpfile)

    def load(self):
        for dumpfile in (self.dumpfile, self.dumpfile_new):
            if os.path.isfile(dumpfile):
                fp = open(dumpfile, 'rb')
                obj = pickle.load(fp)
                fp.close()
                return obj


def change_file_ext(filename, ext):
    return '.'.join(list(os.path.splitext(filename)[:-1]) + [ext])


def we_are_frozen():
    """Returns whether we are frozen via py2exe.
    This will affect how we find out where we are located."""
    return hasattr(sys, 'frozen')


def is_forking():
    # 返回本进程是否是由multiprocessing产生的子进程
    # 参考自 multiprocessing.forking.is_forking
    return len(sys.argv) == 3 and sys.argv[1] == '--multiprocessing-fork'


def module_path(module_name='__main__', module=None, filename=''):
    """ This will get us the program's directory,
    even if we are frozen using py2exe"""

    if not filename:
        filename = module_file(module_name, module)

    result = os.path.abspath(os.path.dirname(filename))

    if result and result[-1] != os.sep:
        result += os.sep
    return result


def module_file(module_name='__main__', module=None):
    result = ''
    if we_are_frozen():
        result = sys.executable
    else:
        if not module and module_name:
            module = sys.modules.get(module_name)

        if module:
            import inspect
            try:
                result = inspect.getfile(module)
            except TypeError:  # TypeError: <module '__main__' (built-in)> is a built-in module
                result = sys.argv[0]

        if not result:
            if sys._getframe().f_back:
                result = sys._getframe().f_back.f_code.co_filename
            else:
                result = __file__

    result = os.path.abspath(result)
    return result


def extenddir(sour, directory):
    path = module_path(sour)
    if directory:
        result = ''.join([path, directory])
    else:
        result = os.path.normpath(path)
    return result



def val(s, default=0):
    try:
        v = int(s)
    except ValueError:
        v = default
    return v



def nullfile():
    import platform
    return '/dev/null' if platform.system() == 'Linux' else 'nul'


SYS_NULLFILE = nullfile()


def get_fileversion(filename):
    import win32api
    info = win32api.GetFileVersionInfo(filename, os.sep)
    ms = info['FileVersionMS']
    ls = info['FileVersionLS']
    version = '%d.%d.%d.%d' % (win32api.HIWORD(ms), win32api.LOWORD(ms), win32api.HIWORD(ls), win32api.LOWORD(ls))
    return version


def get_fileversioninfo(filename):
    """
    Read all properties of the given file return them as a dictionary.
    """
    import win32api
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


def makesure_dirpathexists(dir_or_path_or_file):
    try:
        dir_, file_ = os.path.split(dir_or_path_or_file)
        if '.' not in file_:
            dir_ = os.path.join(dir_, file_)
        os.makedirs(dir_)
    except:  # WindowsError: [Error 183] (路径已存在)
        pass


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


def runas_admin(exefile, param, workdir, showcmd=None):
    import win32api
    import win32con
    import platform
    import pywintypes
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


def disable_deprecationwarnings():
    import warnings
    warnings.filterwarnings('ignore', category=DeprecationWarning)


def getconsolehwnd():
    import win32console
    return win32console.GetConsoleWindow()


def wts_msgbox(msg, title='提示', style=0, timeout=0, wait=False):
    # 这个函数支持在服务程序里弹出对话框
    import win32ts
    sid = win32ts.WTSGetActiveConsoleSessionId()
    if sid != 0xffffffff:
        ret = win32ts.WTSSendMessage(win32ts.WTS_CURRENT_SERVER_HANDLE,
                                     sid, title, msg, style, timeout, wait)
        return ret


def msgbox(msg, title='提示', warning=False, question=False, **kw):
    import win32api
    import win32con
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


def set_exit_handler(func):
    if os.name == 'nt':
        try:
            import win32api
            win32api.SetConsoleCtrlHandler(func, True)
        except ImportError:
            version = '.'.join(map(str, sys.version_info[:2]))
            raise Exception('pywin32 not installed for Python ' + version)
    else:
        import signal
        signal.signal(signal.SIGTERM, func)


def isdebugging():
    # http://stackoverflow.com/questions/333995/how-to-detect-that-python-code-is-being-executed-through-the-debugger/26605963
    import inspect

    for frame in inspect.stack():
        if frame[1].endswith('pydevd.py'):
            return True
    return False


def make_closure(func, *args, **kwargs):
    '''
    Python2.5开始可使用functools.partial()代替此函数
    '''

    def __closeure():
        func(*args, **kwargs)

    return __closeure


def flatten(l):
    y = []
    for x in l:
        if isinstance(x, (list, tuple)):
            y += flatten(x)
        else:
            y += [x]
    return y


def chunk(seq, chunk_len):
    return (seq[i:i + chunk_len] for i in xrange(0, len(seq), chunk_len))


def urlencode_uni(us):
    '''
    将指定的unicode编码的URL转换成ASCII字符串，unicode汉字会编码为%AA%BB的格式。
    如 urlencode_uni(u'cesi测试') 返回 'cesi%6D%4B%8B%D5'
    '''
    l = []
    for c in us:
        n = ord(c)
        if n > 255:
            l.extend(['%%%X' % c for c in (n / 0x100, n % 0x100)])
        else:
            l.append(chr(n))
    return ''.join(l)


def decode_json(s):
    """
    兼容不正确地使用'\'逃逸符的JSON格式
    如\&quot; \&#39; 等
    详见：http://stackoverflow.com/questions/7921164/syntax-error-when-parsing-json-string
    JSON正确性验证：http://jsonlint.com/
    """
    result = None
    if s:
        s = s.replace(r'\&', '')
        try:
            result = json.loads(s)
        except ValueError as e:
            pass
    return result


def json_get(s, key, default=None):
    """
    解析JSON字符串为字典，然后按.分隔的路径获取键值。
    """
    if isinstance(s, basestring):
        d = decode_json(s)
    else:
        d = s
    val = dget(d, key, default=default, separator='.')
    return val


def html_unescape(s):
    import HTMLParser
    parser = HTMLParser.HTMLParser()
    s = s.replace('&nbsp;', '')
    return parser.unescape(s)


def d2s(d, encoding='utf-8'):
    """
    turns dict to human readable string.
    :param d: dict
    :param encoding: unicode decode encoding if there is a multi-bytes str.
    :return: str | unicode
    """
    return json.dumps(d, ensure_ascii=False, encoding=encoding)


def dget(d, path, default=None, separator='/'):
    if isinstance(path, basestring):
        keys = path.split(separator)
    else:  # iterable
        keys = path
    for key in keys:
        d = d.get(key)
        if d is None:
            break
    if d is None:
        d = default
    return d


def dget_int(d, path, default=0, separator='/'):
    v = dget(d, path, default, separator)
    if isinstance(v, (int, long)):
        return v
    if isinstance(v, basestring) and v.isdigit():
        return int(v)
    return default


def _a(u, encoding=SYS_ENCODING, from_encoding=SYS_ENCODING, errors='replace'):
    if isinstance(u, unicode):
        return u.encode(encoding, errors=errors)
    elif encoding.lower().replace('-', '') == from_encoding.lower().replace('-', ''):
        return str(u)
    else:
        return unicode(u, from_encoding).encode(encoding, errors=errors)


def _u(s, encoding=SYS_ENCODING, errors='replace'):
    if isinstance(s, unicode):
        return s
    elif isinstance(s, str):
        return unicode(s, encoding, errors=errors)
    else:  # int, etc..
        # Can't take keyword parameters, otherwise it will raise an error:
        # 	TypeError: coercing to Unicode: need string or buffer, int found
        return unicode(s)


def _u8(s):
    return _u(s, encoding='utf-8')


to_bytes = _a
to_bytes_utf8 = partial(_a, encoding='utf-8', from_encoding='utf-8')
to_unicode = _u
to_unicode_utf8 = _u8


