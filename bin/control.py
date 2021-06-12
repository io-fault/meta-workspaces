"""
# System command interface for controlling and using a workspace context.
# Normally bound as (id)`pdctl`.
"""
import os
import sys

from fault.system import process
from fault.system import files

from .. import system
from .. import operations

# Default relative subdirectory containing cc's, build support, and cache.
WORKSPACE='.workspace'

# Workspace specific; pdctl uses an explicit context set directory.
intention_codes = {
	'g': (+0, 'debug'),
	'O': (+2, 'optimal'),
	'C': (+3, 'coverage'),
	'P': (+3, 'profile'),
	'T': (-1, 'delineation'),

	'A': '..', # All.
}

aliases = {
	'ls': 'project_list',
	'fx': 'execute',
	'init': 'initialize',
}

def intent(options, index=intention_codes):
	for x in options:
		intents = [index[i] for i in set(x[1:]).intersection(intention_codes)]
		if intents:
			intents.sort()
			yield from (i[1] for i in intents)

def rebuild(options):
	re = 0
	for x in options:
		roffset = x.rfind('r')
		Roffset = x.rfind('R')
		if roffset == Roffset == -1:
			continue

		if roffset > Roffset:
			re = 1
		else:
			re = 2

	return re

def split(argv):
	for i, x in zip(range(len(argv)), argv):
		if x == '--' or not x.startswith('-'):
			return argv[:i], argv[i:]

	# All options.
	return argv, []

parameters = {
	'build': (lambda options, argv: {'intentions': intent(options), 'argv': argv, 'rebuild': rebuild(options)}),
	'edit': (lambda options, argv: {'factors': argv}),
}
parameters['sources'] = parameters['edit']
parameters['test'] = parameters['build']

def main(inv:process.Invocation) -> process.Exit:
	i = 0
	r_level = 0
	for i, x in zip(range(len(inv.argv)), inv.argv):
		if x.startswith('-') and x != '--':
			continue

		# Process global options.
		options = inv.argv[:i]
		if options:
			if options[0] == '--':
				# Terminator.
				pass
			elif options[0] == '-r':
				r_level = 1
			elif options[0] == '-R':
				r_level = 2
			else:
				sys.stderr.write("ERROR: unrecognized root option: " + options[0] + "\n")
				return inv.exit(1)

		break
	else:
		# No command issued.
		return inv.exit(254)

	command_id = aliases.get(inv.argv[i], inv.argv[i])

	try:
		Command = getattr(operations, command_id)
	except AttributeError:
		Command = getattr(operations, command_id.replace('-', '_'), None)

	if Command is None:
		sys.stderr.write("ERROR: unrecognized command '" + command_id + "'\n")
		return inv.exit(3)

	command_options, command_argv = split(inv.argv[i+1:])
	if command_id in parameters:
		command_kw = parameters[command_id](command_options, command_argv)
	else:
		command_kw = {}

	if r_level:
		command_kw['rebuild'] = r_level

	# Usually pwd case.
	route = files.pwd()/WORKSPACE
	product = route.container

	works = system.Support(route)
	wkenv = system.Environment(works, product)

	os.environ['PRODUCT'] = str(product)

	status = Command(wkenv, **command_kw)
	sys.stderr.write(status)

	return inv.exit(0)

if __name__ == '__main__':
	process.control(main, process.Invocation.system())
