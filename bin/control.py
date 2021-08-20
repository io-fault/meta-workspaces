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
	'I': (+1, 'identity'),
	'O': (+2, 'optimal'),
	'o': (+3, 'portable'),

	'g': (+4, 'debug'),
	'U': (+5, 'auxilary'),
	'Y': (+6, 'capture'),

	'P': (+8, 'profile'),
	'C': (+9, 'coverage'),
}

intention_set = {
	i[1]: code for code, i in intention_codes.items()
}

aliases = {
	'ls': 'project_list',
	'fx': 'execute',
	'init': 'initialize',
}

def intent(options, index=intention_codes, All='A', Except='a'):
	bitop = 0 # 0 is whitelist, 1 is all, -1 is blacklist
	identified = set()

	for x in options:
		optset = set(x[1:])
		if All in optset:
			identified = set(intention_codes.values())
			bitop = 1
			break
		elif Except in optset:
			bitop = -1

		for i in optset.intersection(intention_codes):
			identified.add(index[i])

		if 'a' in optset:
			bitop = -1

	if bitop == -1:
		# Blacklist
		filtered = [x for x in intention_codes.values() if x not in identified]
		identified = filtered

	return [x[1] for x in sorted(identified)]

def relevel(options):
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
	'build': (lambda options, argv: {'intentions': intent(options), 'argv': argv, 'relevel': relevel(options)}),
	'edit': (lambda options, argv: {'factors': argv}),
}
parameters['sources'] = parameters['edit']
parameters['test'] = parameters['build']
parameters['initialize'] = parameters['build']
parameters['delineate'] = parameters['build']

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
		command_kw['relevel'] = r_level

	# Usually pwd case.
	route = files.pwd()/WORKSPACE
	product = route.container

	works = system.Tooling(route)
	wkenv = system.Environment(works, product)

	os.environ['F_PRODUCT'] = str(route/'cc')
	os.environ['PRODUCT'] = str(product)

	status = Command(wkenv, Command=command_id, **command_kw)
	sys.stderr.write(status)

	return inv.exit(0)

if __name__ == '__main__':
	process.control(main, process.Invocation.system())
