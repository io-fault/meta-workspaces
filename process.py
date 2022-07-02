"""
# Factor processing operations for build, test, delineate, and analyze.
"""
import sys
import os
from collections.abc import Set

from fault.time.sysclock import now

from fault.context import tools
from fault.project import system as lsf
from fault.system import files

from fault.transcript import terminal
from fault.transcript import execution
from fault.transcript.io import Log
from fault.transcript.metrics import Procedure
from fault.project import graph

from . import system

# Initialize workspace environment and project index.
def initialize(wkenv:system.Environment, config, command, *argv):
	from . import initialization

	if initialization.root(wkenv, config['intentions'], relevel) >= 0:
		summary = "workspace context initialized\n"
	else:
		summary = "workspace directory already exists\n"

	return summary

# Build the product or a project set.
def _process(wkenv, command, intentions, argv, ident, form=''):
	from system.root.query import dispatch
	from fault.system.execution import KInvocation

	env, exepath, xargv = dispatch('factors-cc')

	cache = wkenv.build_cache
	ccs = [wkenv.work_construction_context]
	pj = wkenv.work_project_context.project(ident)

	for ccontext in ccs:
		fpath = str(pj.factor)

		cmd = xargv + [
			str(ccontext), 'persistent', str(cache),
			form + '/' + ':'.join(intentions),
			str(wkenv.work_product_route), str(pj.factor)
		]
		cmd.extend(argv[1:])
		ki = KInvocation(cmd[0], cmd)
		yield (fpath, (), None, ki)

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

def build(wkenv:system.Environment,
		command:str, # build or delineate
		intentions:Set[str],
		relevel,
		lanes,
		symbols
	):
	from fault.transcript import proctheme

	lanes = int(lanes)
	os.environ['FPI_REBUILD'] = str(relevel)
	wkenv.load()

	explicit = None
	if symbols and symbols[0] != '.':
		fpath = lsf.types.factor@symbols[0]
		try:
			explicit = [wkenv.work_project_context.split(fpath)[1].identifier]
		except LookupError:
			explicit = [
				pj.identifier for pj in wkenv.work_project_context.iterprojects()
				if pj.factor.segment(fpath)
			]

	limit = min(lanes, len(explicit) if explicit is not None else lanes)
	control = terminal.setup()
	control.configure(limit+1)

	monitors, summary = terminal.aggregate(control, proctheme, limit, width=180)
	if command == 'delineate':
		cform = 'delineated'
	else:
		cform = ''

	i = tools.partial(_process, wkenv, command, intentions, symbols, form=cform)

	if explicit is not None:
		q = SQueue(explicit)
	else:
		q = graph.Queue()
		q.extend(wkenv.work_project_context)

	meta = Log.stderr()
	log = Log.stdout()
	xid = 'build'
	log.xact_open(xid, "FPI: %s." %(command,), {})
	try:
		execution.dispatch(meta, log, i, control, monitors, summary, "FPI", q,)
	finally:
		log.xact_close(xid, summary.synopsis(), {})

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

def plan_test(wkenv:system.Environment, intention:str, argv, pcontext:lsf.Context, identifier):
	"""
	# Create an invocation for processing the project from &pcontext selected using &identifier.
	"""
	from fault.system.execution import KInvocation
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

		pj_fp = str(project)
		test_fp = str(fp)
		xid = '/'.join((pj_fp, test_fp))

		cmd = xargv + [
			'fault.test.bin.coherence',
			pj_fp, test_fp
		]
		env = dict(os.environ)
		env.update(exeenv)
		env['F_PROJECT'] = str(project)
		ki = KInvocation(cmd[0], cmd, environ=env)

		yield (pj_fp, (test_fp,), xid, ki)

def test(
		wkenv:system.Environment,
		command:str,
		intentions:Set[str],
		relevel:int,
		lanes:int,
		selection,
	):
	from fault.transcript import fatetheme

	# Project Context
	metrics = Procedure.create()
	lanes = int(lanes)
	wkenv.load()
	os.environ['F_PRODUCT'] = str(wkenv.work_product_route)

	control = terminal.setup()
	control.configure(lanes+1)
	monitors, summary = terminal.aggregate(control, fatetheme, lanes, width=160)
	status = (control, monitors, summary)

	if not selection or '.' in selection:
		explicit = None
	else:
		explicit = []
		for fpathstr in selection[:1]:
			fpath = lsf.types.factor@fpathstr
			try:
				explicit.append(wkenv.work_project_context.split(fpath)[1].identifier)
			except LookupError:
				explicit.extend(
					pj.identifier for pj in wkenv.work_project_context.iterprojects()
					if pj.factor.segment(fpath)
				)

	meta = Log.stderr()
	log = Log.stdout()

	for intent in intentions:
		xid = 'test/' + intent
		log.xact_open(xid, "Testing %s." %(intent,), {})
		try:
			os.environ['INTENTION'] = intent

			# The queues have state, so they must be rebuilt for each intention.
			if explicit is not None:
				q = SQueue(explicit)
			else:
				q = graph.Queue()
				q.extend(wkenv.work_project_context)

			i = tools.partial(plan_test, wkenv, intent, selection[1:], wkenv.work_project_context)

			execution.dispatch(meta, log, i, control, monitors, summary, "Fates", q,)
			metrics += summary.profile()[-1]
		finally:
			summary.title('Fates', intent)
			log.xact_close(xid, summary.synopsis(), {})
