"""
# System command interface for controlling and using a workspace context.
# Normally bound as (id)`pdctl`.
"""
import os
import sys

from fault.vector import recognition
from fault.system import process
from fault.system import files

from .. import system
from .. import operations

root_restricted = {
	'-I': ('set-add', 'identity', 'intentions'),
	'-O': ('set-add', 'optimal', 'intentions'),
	'-o': ('set-add', 'portable', 'intentions'),
	'-g': ('set-add', 'debug', 'intentions'),
	'-y': ('set-add', 'auxilary', 'intentions'),
	'-Y': ('set-add', 'capture', 'intentions'),
	'-P': ('set-add', 'profile', 'intentions'),
	'-C': ('set-add', 'coverage', 'intentions'),

	'-U': ('field-replace', -1, 'relevel'),
	'-u': ('field-replace', 0, 'relevel'),
	'-r': ('field-replace', 1, 'relevel'),
	'-R': ('field-replace', 2, 'relevel'),
	'-.': ('ignore', None, None),
}

root_required = {
	'-i': ('set-add', 'intentions'),
	'-x': ('field-replace', 'construction-context'),
	'-W': ('field-replace', 'workspace-directory'),
	'-D': ('field-replace', 'product-directory'),
	'-L': ('field-replace', 'processing-lanes'),
}

# Default relative subdirectory containing cc's, build support, and cache.
WORKSPACE='.workspace'

def main(inv:process.Invocation) -> process.Exit:
	config = {
		'intentions': set(),
		'relevel': 0,
		'processing-lanes': 4,
		'construction-context': None,
		'workspace-directory': None,
		'product-directory': None,
	}
	oeg = recognition.legacy(root_restricted, root_required, inv.argv)
	remainder = recognition.merge(config, oeg)

	if not remainder:
		# No command issued.
		return inv.exit(254)

	command_id = remainder[0].replace('-', '_')

	try:
		Command = getattr(operations, command_id)
	except AttributeError:
		sys.stderr.write("ERROR: unrecognized command '" + command_id + "'\n")
		return inv.exit(3)

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

	works = system.Tooling(route)
	wkenv = system.Environment(works, product, cctx)
	status = Command(wkenv, config, *remainder)
	sys.stderr.write(status)

	return inv.exit(0)

if __name__ == '__main__':
	process.control(main, process.Invocation.system())
