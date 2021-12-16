"""
# System command interface for controlling and using a workspace context.
# Normally bound as (id)`wkctl`.
"""
import os
import sys
import importlib

from fault.vector import recognition
from fault.system import process
from fault.system import files

from .. import system
from .. import __name__ as project_package_name

restricted = {
	'-I': ('set-add', 'identity', 'intentions'),
	'-O': ('set-add', 'optimal', 'intentions'),
	'-o': ('set-add', 'portable', 'intentions'),
	'-g': ('set-add', 'debug', 'intentions'),

	'-y': ('set-add', 'auxilary', 'intentions'),
	'-Y': ('set-add', 'capture', 'intentions'),

	'-P': ('set-add', 'profile', 'intentions'),
	'-C': ('set-add', 'coverage', 'intentions'),

	'-U': ('field-replace', -1, 'relevel'),
	'-u': ('field-replace', +0, 'relevel'),
	'-r': ('field-replace', +1, 'relevel'),
	'-R': ('field-replace', +2, 'relevel'),
	'-.': ('ignore', None, None),
}

required = {
	'-i': ('set-add', 'intentions'),
	'-x': ('field-replace', 'construction-context'),
	'-W': ('field-replace', 'workspace-directory'),
	'-D': ('field-replace', 'product-directory'),
	'-L': ('field-replace', 'processing-lanes'),
}

# Default relative subdirectory containing cc's, build support, and cache.
WORKSPACE='.workspace'

command_index = {
	# Build factor integrals, execute test factors.
	'build': (
		'.process', 'build',
		({}, {}),
		'command', 'intentions', 'relevel', 'processing-lanes', 'argv',
	),
	'test': (
		'.process', 'test',
		({}, {}),
		'command', 'intentions', 'relevel', 'processing-lanes', 'argv',
	),

	# Delineate factor sources, analyze factor fragments.
	'delineate': (
		# Delineation is recognized by the command identifier.
		'.process', 'build',
		({}, {}),
		'command', 'intentions', 'relevel', 'processing-lanes', 'argv',
	),
	'analyze': (
		'.process', 'analyze',
		({}, {}),
		'command', 'intentions', 'processing-lanes', 'argv',
	),

	# Clear build cache, clean product integrals.
	'clear': (
		'.manipulation', 'clear',
		({}, {}),
	),
	'clean': (
		'.manipulation', 'clean',
		({}, {}),
	),
}

def main(inv:process.Invocation) -> process.Exit:
	config = {
		'argv': (),
		'command': None,
		'intentions': set(),
		'relevel': '0',
		'processing-lanes': '4',
		'construction-context': None,
		'workspace-directory': None,
		'product-directory': None,
	}
	oeg = recognition.legacy(restricted, required, inv.argv)
	remainder = recognition.merge(config, oeg)

	if not remainder:
		# No command issued.
		return inv.exit(254)

	command_id = config['command'] = remainder[0]
	config['argv'] = remainder[1:]
	del remainder

	if command_id not in command_index:
		sys.stderr.write("ERROR: unknown command %r\n" %(command_id,))
		return inv.exit(253)

	module_name, opname, opargs, *opconfig = command_index[command_id]
	module = importlib.import_module(module_name, project_package_name)
	opcall = getattr(module, opname)

	if config['product-directory'] is None:
		product = process.fs_pwd()
	else:
		product = files.Path.from_path(config['product-directory'])
	os.environ['PRODUCT'] = str(product)

	if config['workspace-directory'] is None:
		route = product/WORKSPACE
	else:
		route = files.Path.from_path(config['workspace-directory'])

	# Override .workspace/cc default? Option consistent with pdctl.
	if config['construction-context'] is None:
		cctx = (route/'cc')
	else:
		cctx = files.Path.from_path(config['construction-context'])

	os.environ['F_PRODUCT'] = str(cctx)

	works = system.Tooling(cctx/'tools')
	wkenv = system.Environment(works, product, cctx)

	status = opcall(wkenv, *[config.get(x) for x in opconfig])
	return inv.exit(0)

if __name__ == '__main__':
	process.control(main, process.Invocation.system())
