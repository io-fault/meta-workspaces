"""
# High-level workspace operations usually dispatched by &.bin.control.

# Operations either return a summary string or raise and error citing the failure and exit code to use.
"""
import collections
import sys
import os
import functools

from fault.context import tools
from fault.system import execution
from fault.system import query
from fault.system import files
from fault.project import system as lsf

from .system import Environment

NoSummary = ""

def system(command, argv, name=None):
	ki = execution.KInvocation(command, [name or command] + argv)
	pid = ki.spawn(fdmap=[(0,0), (1,1), (2,2)])
	return pid, execution.reap(pid, options=0)

def srcindex(wkenv, factors):
	for afpath in factors:
		pd, pj, fpath = wkenv.work_project_context.split(lsf.types.factor@afpath)
		for (fp, ft), (fy, fs) in pj.select(fpath.container):
			if fp == fpath or fp.segment(fpath):
				yield from fs

def update(wkenv:Environment):
	wkenv.load()

	pd = wkenv.work_product_index
	pd.clear()
	pd.update()
	pd.store()
	return ""

def status(wkenv:Environment):
	wkenv.load()
	sys.stderr.write(f"CONTEXT[cwd-connect]: {wkenv.work_product_route}\n")
	return NoSummary

# Initialize workspace environment and project index.
def initialize(wkenv:Environment, clear=False):
	from . import initialization
	initialization.root(wkenv)
	return "workspace context initialized\n"

# Launch EDITOR for resolved sources.
def edit(wkenv:Environment, factors=[], project:str=None):
	system_command = os.environ['EDITOR']
	if system_command[:1] != '/':
		system_command, = query.executables(system_command) # EDITOR not in environment?

	wkenv.load()

	pwd = str(files.Path.from_absolute(os.environ['PWD'])) + '/'
	l = len(pwd)
	sources = [
		x[l:] if x.startswith(pwd) else x
		for x in
		map(str, (y[1] for y in srcindex(wkenv, factors)))
	]

	os.execv(system_command, [system_command] + sources)

# List sources.
def sources(wkenv:Environment, factors=[], project:str=None):
	wkenv.load()

	for f in srcindex(wkenv, factors):
		sys.stdout.write(str(f) + '\n')

	return NoSummary

# List projects or contexts.
def project_list(wkenv:Environment, type='project'):
	wkenv.load()
	ls = '\n'.join(str(pj.factor) for pj in wkenv.iterprojects())
	sys.stdout.write(ls + '\n')

	return NoSummary

# Build the product or a project set.
def _build(wkenv, command, intentions, argv, ident):
	from system.root.query import dispatch
	env, exepath, xargv = dispatch('factors-cc')

	cache = wkenv.build_cache
	ccs = wkenv.work_space_tooling.ccset()
	pj = wkenv.work_project_context.project(ident)

	for ccontext in ccs:
		dims = (str(pj.factor),)
		xid = '/'.join(dims)

		cmd = xargv + [
			str(ccontext), 'persistent', str(cache),
			':'.join(intentions),
			str(wkenv.work_product_route), str(pj.factor)
		]
		cmd.extend(argv[1:])
		ki = execution.KInvocation(cmd[0], cmd)
		yield ('FPI', dims, xid, None, ki)

class SQueue(object):
	def __init__(self, sequence):
		self.items = list(sequence)
		self.count = len(self.items)

	def take(self, i):
		r = self.items[:i]
		del self.items[:i]
		return r

	def finish(self, *items):
		pass

	def terminal(self):
		return not self.items

	def status(self):
		return (self.count - len(self.items), self.count)

def build(wkenv:Environment, intentions, argv=[], rebuild=0):
	from fault.time.sysclock import now
	from fault.project import graph
	from fault.transcript import execution
	from fault.transcript import terminal
	from fault.transcript import integration
	from fault.transcript import proctheme

	if rebuild:
		os.environ['FPI_REBUILD'] = str(rebuild)

	wkenv.load()

	control = terminal.setup()
	control.configure(5)

	explicit = None
	if argv and argv[0] != '.':
		fpath = lsf.types.factor@argv[0]
		try:
			explicit = [wkenv.work_project_context.split(fpath)[1].identifier]
		except LookupError:
			explicit = [
				pj.identifier for pj in wkenv.work_project_context.iterprojects()
				if pj.factor.segment(fpath)
			]

	build_reporter = integration.emitter(integration.factor_report, sys.stdout.write)
	build_traps = execution.Traps.construct(eox=integration.select_failures, eop=build_reporter)

	monitors, summary = terminal.aggregate(control, proctheme, 4, width=180)
	i = functools.partial(_build, wkenv, 'build', intentions, argv)

	if explicit is not None:
		q = SQueue(explicit)
	else:
		q = graph.Queue()
		q.extend(wkenv.work_project_context)

	constants = ('build',)
	execution.dispatch(build_traps, i, control, monitors, summary, "FPI", constants, q)

	return NoSummary

# Execute workspace subject factor.
def execute(wkenv:Environment, argv=[]):
	wkenv.load()
	works = wkenv.work_space_tooling
	works.load()

	str(wkenv.work_product_route)

def check_keywords(keywords, name, Table=str.maketrans('_.-', '   ')):
	name_str = str(name)
	name_set = set(str(name).translate(Table).split())
	empty_constraints = 0

	for k in keywords:
		ccode = k[:1]

		if ccode == '@':
			if name_str == k[1:]:
				return True
		elif ccode == '.':
			if name_str.endswith(k[1:]):
				return True
		elif ccode == '+':
			# Whitelist
			if k[1:] in name_set:
				return True
		elif ccode == '-':
			# Blacklist
			if k[1:] in name_set:
				return False
		elif k in name_str:
			return True
		else:
			if k.strip() == '':
				empty_constraints += 1

	# False, normally. True when all the keywords were whitespace.
	return len(keywords) == empty_constraints

def plan_test(wkenv:Environment, intention:str, argv, pcontext:lsf.Context, identifier):
	"""
	# Create an invocation for processing the project from &pcontext selected using &identifier.
	"""

	pj = pcontext.project(identifier)
	project = pj.factor

	from system.root import query
	exeenv, exepath, xargv = query.dispatch('python')
	xargv.append('-d')

	if argv:
		kwcheck = (lambda x: check_keywords(argv, x))
	else:
		kwcheck = (lambda x: True) # Always true if unconstrainted

	for (fp, ft), fd in pj.select(lsf.types.factor@'test'):
		if not fp.identifier.startswith('test_') or not kwcheck(fp):
			continue

		cmd = xargv + [
			'fault.test.bin.coherence',
			str(project), str(fp)
		]
		env = dict(os.environ)
		env.update(exeenv)
		env['F_PROJECT'] = str(project)
		ki = execution.KInvocation(cmd[0], cmd, environ=env)

		dims = (str(project), str(fp))
		xid = '/'.join(dims)
		yield ('Fates', dims, xid, None, ki)

# Debug intention (default) test execution with interactive control. -g
def test(wkenv:Environment, intentions, argv=[], rebuild=1, lanes=4):
	from fault.transcript import terminal
	from fault.transcript import integration
	from fault.transcript import fatetheme
	from fault.transcript import execution
	from fault.project import graph

	# Project Context
	wkenv.load()
	os.environ['F_PRODUCT'] = str(wkenv.work_product_route)

	control = terminal.setup()
	control.configure(lanes+1)
	monitors, summary = terminal.aggregate(control, fatetheme, lanes, width=160)
	status = (control, monitors, summary)

	test_reporter = integration.emitter(integration.test_report, sys.stdout.write)
	test_traps = execution.Traps.construct(eop=test_reporter)

	if not argv or '.' in argv:
		explicit = None
	else:
		explicit = []
		for fpathstr in argv[:1]:
			fpath = lsf.types.factor@fpathstr
			try:
				explicit.append(wkenv.work_project_context.split(fpath)[1].identifier)
			except LookupError:
				explicit.extend(
					pj.identifier for pj in wkenv.work_project_context.iterprojects()
					if pj.factor.segment(fpath)
				)
		del argv[:1]

	for intent in intentions:
		os.environ['INTENTION'] = intent

		# The queues have state, so they must be rebuilt for each intention.
		if explicit is not None:
			q = SQueue(explicit)
		else:
			q = graph.Queue()
			q.extend(wkenv.work_project_context)

		local_plan = tools.partial(plan_test, wkenv, intent, argv, wkenv.work_project_context)

		sys.stdout.write("[-> Testing %r build. (integrate/test)]\n" %(intent,))
		constants = ('test', intent)
		try:
			execution.dispatch(test_traps, local_plan, control, monitors, summary, "Fates", constants, q)
		finally:
			summary.set_field_read_type('usage', 'overall')
			sys.stdout.write("[<- %s (integrate/test)]\n" %(summary.synopsis(),))

	return ""

def clear():
	"""
	# Clear build cache.
	"""
	return "No effect."

def clean(intentions=[],):
	"""
	# Remove factor images for the given intentions.
	"""
	return "No effect."

def help(wkenv:Environment, argv=[]):
	"""
	# Display help for command list and command information.
	"""
	pass
