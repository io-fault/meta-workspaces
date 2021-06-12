"""
# Workspace APIs interrogating context directories and product directories on the local system.

# This module provides interfaces for two interests: a local Product directory containing
# the projects being developed or analyzed(subject), a workspace context directory containing the
# construction contexts and build tool support.
"""
import typing

from fault.system import files
from fault.project.root import Product, Project, Context
from fault.project.types import factor

class Support(object):
	"""
	# Support directory interface providing access to Construction Contexts and integration tools.
	"""

	def __init__(self, route:files.Path, Context=Context):
		self.route = route
		self.tool_context = Context()
		self.tool_index = None

	def load(self):
		"""
		# Load the workspace tools context.
		"""
		self.tool_index = self.tool_context.connect(self.route/'tools')
		self.tool_context.load()

	def ccset(self, intention:str) -> typing.Iterator[files.Path]:
		"""
		# Resolve (construction) context set path for the given intention.
		"""
		return (self.route/'cc'/intention).fs_iterfiles(type='directory')

class Environment(object):
	"""
	# A sole product referring to the subject projects and a workspace &Support directory.
	"""

	work_project_context: Context = None
	work_product_index: Product = None
	work_product_route: files.Path = None
	work_space_support: Support = None

	def __init__(self, works:Support, product:files.Path, Context=Context):
		self.work_project_context = Context() # Subject/Target Set
		self.work_space_support = works
		self.work_product_route = product

	@property
	def detached(self) -> bool:
		"""
		# Whether the workspace context is contained in the subject product directory.
		"""
		return self.work_space_support.route.container == self.work_product_route

	@property
	def build_cache(self) -> files.Path:
		return self.work_space_support.route / 'cache'

	@property
	def project_count(self) -> int:
		"""
		# Number of subject projects present in the environment.
		"""
		return len(self.work_project_context.instance_cache)

	def iterprojects(self) -> Project:
		"""
		# Iterate over all focused subject projects.
		"""
		return self.work_project_context.iterprojects()

	def load(self):
		"""
		# Initialize the project &Context and recognize the &Product index.
		"""
		# Single product context.
		self.work_product_index = self.work_project_context.connect(self.work_product_route)
		self.work_project_context.load()
		self.work_project_context.configure()

	def select(self, project:str) -> Project:
		"""
		# Get the &Project instance for the given &project path from the environment's project context.
		"""
		pj = None
		pd = self.work_product_index

		for pj in pd.select(factor@project):
			break
		else:
			raise LookupError("no such project in workspace environment")

		pj_id = pd.identifier_by_factor(pj)
		return self.work_project_context.project(pj_id[0])
