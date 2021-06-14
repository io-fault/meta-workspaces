"""
# Workspace initialization procedures.
"""
import os

directory_paths = [
	'cc', # Construction Context
	'cache', # Build cache.
	'captures',
]

intentions = [
	'optimal',
	'debug',
	'coverage',
	'profile',
]

def cc(route):
	import system.factors.bin.initialize as init
	import system.machine.bin.setup as sysi
	import system.python.bin.setup as pyi

	for i in intentions:
		ccr = (route/i/'host').fs_alloc()
		init.context(ccr, i, {}, set())
		ctx = pyi.cc.Context.from_directory(ccr)
		sysi.install(ccr, ctx, 'fault', ['CC', os.environ.get('CC') or '/usr/bin/cc'])
		pyi.install(ccr, ctx, {})

def directories(route):
	(route).fs_mkdir()
	for x in directory_paths:
		(route@x).fs_mkdir()

def root(wkenv):
	route = wkenv.work_space_tooling.route
	directories(route)
	cc(route/'cc')
