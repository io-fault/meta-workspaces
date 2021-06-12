"""
# Initialization routines for setting up workspace contexts.
"""

directory_paths = [
	'cc', # Construction Context
	'cache', # Build cache.
	'captures', # Measurements (coverage/profiling)
]

def directories(route):
	(route).fs_mkdir()

	for x in directory_paths:
		(route@x).fs_mkdir()
