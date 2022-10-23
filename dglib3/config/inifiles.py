from __future__ import absolute_import

import re
import itertools
from configparser import RawConfigParser, NoSectionError, NoOptionError, DEFAULTSECT

from ..basis.ordered_dict import OrderedDictCaseInsensitive
from ..utils import SYS_ENCODING


class IniFile(RawConfigParser):
    def __init__(self, filename=None, encoding=None, get_unicode=False, compact=False):
        RawConfigParser.__init__(self, dict_type=OrderedDictCaseInsensitive)
        if encoding is None:
            encoding = SYS_ENCODING
        self._encoding = encoding
        self._get_unicode = get_unicode
        self._compact = compact
        self.filename = ''
        if filename:
            self.load(filename)

    def load(self, filename=None):
        if not filename:
            filename = self.filename
        else:
            self.filename = filename

        try:
            with open(filename) as fp:
                if self._encoding == 'utf-8-sig':
                    # skip BOM
                    fp.read(3)

                self.read_file(fp, filename)
        except IOError:
            return

    def save(self, filename=None):
        filename = filename or self.filename

        with open(filename, 'wb') as fp:
            if self._encoding == 'utf-8-sig':
                # write BOM
                fp.write(b'\xef\xbb\xbf')

            self.write(fp)

    def encode(self, text):
        encoding = self._encoding
        if encoding == 'utf-8-sig':
            encoding = 'utf-8'
        return text.encode(encoding)

    def decode(self, bytes_):
        encoding = self._encoding
        if encoding == 'utf-8-sig':
            encoding = 'utf-8'
        return bytes_.decode(encoding)

    def set(self, section, option, value=None):
        if not self.has_section(section):
            self.add_section(section)
        elif not isinstance(value, str):
            value = str(value)
        RawConfigParser.set(self, section, option, value)

    def _get(self, section, option, default=''):
        try:
            value = RawConfigParser.get(self, section, option)
        except Exception as e:
            if isinstance(e, (NoSectionError, NoOptionError)):
                return default
            raise e
        return value

    def get(self, *args, **kw):
        if self._get_unicode:
            return self.getunicode(*args, **kw)
        else:
            return self._get(*args, **kw)

    def getunicode(self, section, option, default=u''):
        value = self._get(section, option, default)
        if not isinstance(value, str):
            value = str(value, self._encoding)
        return value

    def getint(self, section, option, default=0):
        value = self.get(section, option)
        if re.match(r'-?\d+$', value):
            return int(value)
        else:
            return default

    def getfloat(self, section, option, default=0.):
        value = self.get(section, option)
        if re.match(r'-?\d*?\.?\d+$', value):
            return float(value)
        else:
            return default

    def _join_multiline_values(self):
        defaults = self.default_section, self._defaults
        all_sections = itertools.chain((defaults,), self._sections.items())
        for section, options in all_sections:
            for name, val in options.copy().items():   # copy() to avoid "RuntimeError: OrderedDict mutated during iteration"
                if isinstance(val, list):
                    val = '\n'.join(val).rstrip()
                options[name] = self._interpolation.before_read(self, section, name, val)

    # overloaded (no lower)
    def optionxform(self, optionstr):
        return optionstr

    # overloaded (key = val -> key=val ?)
    def write(self, fp):
        """Write an .ini-format representation of the configuration state."""

        def to_bytes(s):
            result = str(s).encode(self._encoding) if not isinstance(s, str) else self.encode(s)
            return result

        if self._defaults:
            fp.write(b'[%s]\n' % to_bytes(DEFAULTSECT))
            for (key, value) in self._defaults.items():
                fp.write(b'%s = %s\n' % (to_bytes(key), to_bytes(value).replace('\n', '\n\t')))
            fp.write(b'\n')
        for section in self._sections:
            fp.write(b'[%s]\n' % to_bytes(section))
            for (key, value) in self._sections[section].items():
                if key == '__name__':
                    continue
                if (value is not None) or (self._optcre == self.OPTCRE):
                    val = to_bytes(value).replace(b'\n', b'\n\t')
                    if self._compact:
                        line = b'='.join((to_bytes(key), val))
                    else:
                        line = b' = '.join((to_bytes(key), val))
                else:
                    line = key  # value is None and self._optcre == OPTCRE_NV
                fp.write(b'%s\n' % line)
            fp.write(b'\n')


def test():
    ini = IniFile('test.ini')
    name = ini.get('option', 'name', 'aaa')
    print(name)
    name += str(len(name))
    ini.set('option', 'name', name)
    ini.save()


if __name__ == '__main__':
    test()
