"""
# Workspace initialization procedures.
"""
import os

directory_paths = [
	'cc', # Construction Context
	'xc', # Execution Context
	'cache', # Build cache.
	'captures',
]

def cc(route, intentions):
	import system.factors.bin.initialize as init
	import system.machine.bin.setup as sysi
	import system.python.bin.setup as pyi

	ccr = None
	ccr = (route).fs_alloc().fs_mkdir()
	init.context(ccr, 'optimal', {}, set())
	ctx = pyi.cc.Context.from_directory(ccr)
	sysi.install(ccr, ctx, 'fault', ['CC', os.environ.get('CC') or '/usr/bin/cc'])
	pyi.install(ccr, ctx, {})

def directories(route):
	(route).fs_mkdir()
	for x in directory_paths:
		(route@x).fs_mkdir()

def root(wkenv, intentions, relevel):
	route = wkenv.work_space_tooling.route

	if relevel:
		if relevel == 2:
			directories(route)
		elif relevel == 1:
			# Overwrite inplace.
			pass
		else:
			raise ValueError("invalid relevel") # 0, 1, or 2
	else:
		if route.fs_type() != 'void':
			# Already exist and -rR not specified.
			return -1
		directories(route)

	cc(route/'cc', intentions)
	return len(intentions)
