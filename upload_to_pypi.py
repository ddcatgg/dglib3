import sys
import os
import re
import subprocess


def make_egg():
	cmdline = 'python setup.py egg_info'
	p = subprocess.Popen(cmdline)
	ret = p.wait()
	return ret


def make_wheel():
	try:
		import wheel
	except ImportError:
		raise Exception('You need wheel, pip install wheel!')
	cmdline = 'python setup.py bdist_wheel'
	p = subprocess.Popen(cmdline, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	stdout_str = p.stdout.read()
	stderr_str = p.stderr.read()
	ret = p.wait()
	print(stdout_str)
	print(stderr_str)

	# creating build\bdist.win32\wheel\dglib3-0.0.1.dist-info\WHEEL
	pattern = rb'^creating build\\bdist\.win32\\wheel\\([^-]+)-(.+?)\.dist-info\\WHEEL'
	m = re.search(pattern, stdout_str, re.I|re.M)
	pkg_name, pkg_ver = None, None
	if m:
		pkg_name, pkg_ver = map(bytes.decode, m.groups())
	return ret, pkg_name, pkg_ver


def upload_wheel(pkg_name, pkg_ver, py_ver='3'):
	try:
		import twine
	except ImportError:
		raise Exception('You need twine, pip install twine!')
	cmdline = 'twine upload dist/%s-%s-py%s-none-any.whl' % (pkg_name, pkg_ver, py_ver)
	p = subprocess.Popen(cmdline)
	ret = p.wait()
	return ret


def main():
	ret = make_egg()
	if ret != 0:
		os.system('pause')
		sys.exit(ret)

	ret, pkg_name, pkg_ver = make_wheel()
	if ret != 0 or not all([pkg_name, pkg_ver]):
		os.system('pause')
		sys.exit(ret)

	print(pkg_name, pkg_ver)
	ret = upload_wheel(pkg_name, pkg_ver)
	if ret != 0:
		os.system('pause')

	sys.exit(ret)


if __name__ == '__main__':
	main()
