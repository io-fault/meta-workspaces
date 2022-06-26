"""
# Workspace APIs interrogating context directories and product directories on the local system.

# This module provides interfaces for two interests: a local Product directory containing
# the projects being developed or analyzed(subject), a workspace context directory containing the
# construction contexts and build tool support.
"""
import typing

from fault.system import files
from fault.project import system as lsf

class Tooling(object):
	"""
	# Support directory interface providing access to Construction Contexts and integration tools.
	"""

	def __init__(self, route:files.Path, Context=lsf.Context):
		self.route = route
		self.tool_context = Context()
		self.tool_index = None

	def load(self):
		"""
		# Load the workspace tools context.
		"""
		self.tool_index = self.tool_context.connect(self.route/'tools')
		self.tool_context.load()

class Environment(object):
	"""
	# A sole product referring to the subject projects and a &Tooling instance.
	"""

	work_project_context: lsf.Context = None
	work_product_index: lsf.Product = None
	work_product_route: files.Path = None
	work_space_tooling: Tooling = None
	work_construction_context: files.Path = None
	work_execution_context: files.Path = None

	def __init__(self, works:Tooling, product:files.Path, cc:files.Path, xc:files.Path):
		self.work_project_context = lsf.Context() # Subject/Target Set
		self.work_space_tooling = works
		self.work_product_route = product
		self.work_construction_context = cc
		self.work_execution_context = xc

	@property
	def detached(self) -> bool:
		"""
		# Whether the workspace context is contained in the subject product directory.
		"""
		return self.work_space_tooling.route.container == self.work_product_route

	@property
	def build_cache(self) -> files.Path:
		return self.work_space_tooling.route / 'cache'

	@property
	def project_count(self) -> int:
		"""
		# Number of subject projects present in the environment.
		"""
		return len(self.work_project_context.instance_cache)

	def iterprojects(self) -> lsf.Project:
		"""
		# Iterate over all focused subject projects.
		"""
		return self.work_project_context.iterprojects()

	def load(self):
		"""
		# Initialize the project &lsf.Context and recognize the &lsf.Product index.
		"""
		# Single product context.
		self.work_product_index = self.work_project_context.connect(self.work_product_route)
		self.work_project_context.load()
		self.work_project_context.configure()

	def select(self, project:str) -> lsf.Project:
		"""
		# Get the &lsf.Project instance for the given &project path from the environment's project context.
		"""
		pj = None
		pd = self.work_product_index

		for pj in pd.select(lsf.types.factor@project):
			break
		else:
			raise LookupError("no such project in workspace environment")

		pj_id = pd.identifier_by_factor(pj)
		return self.work_project_context.project(pj_id[0])
