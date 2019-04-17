# -*- coding: utf-8 -*-


def html_unescape(s):
    import html
    return html.unescape(s)


def urlencode_uni(us):
    """
    将指定的 unicode 编码的 URL 转换成 ASCII 字符串，unicode 汉字会编码为 %AA%BB 的格式。
    如 urlencode_uni(u'cesi测试') 返回 'cesi%6D%4B%8B%D5'
    """
    list_ = []
    for c in us:
        n = ord(c)
        if n > 255:
            list_.extend(['%%%X' % c for c in (n / 0x100, n % 0x100)])
        else:
            list_.append(chr(n))
    return ''.join(list_)
