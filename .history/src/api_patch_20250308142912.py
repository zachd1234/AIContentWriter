"""
This module patches the Python import system to handle 'api' imports correctly.
Place this at the project root and import it before any other imports.
"""
import sys
import os
import importlib.util
import importlib.machinery

# Get the project root directory
project_root = os.path.dirname(os.path.abspath(__file__))

# Define a custom meta path finder for 'api' imports
class ApiImportFinder:
    def find_spec(self, fullname, path, target=None):
        # Only handle 'api' package and its submodules
        if fullname == 'api' or fullname.startswith('api.'):
            # For the 'api' package itself
            if fullname == 'api':
                api_path = os.path.join(project_root, 'src', 'api')
                if os.path.exists(api_path):
                    return importlib.machinery.ModuleSpec(
                        name=fullname,
                        loader=importlib.machinery.SourceFileLoader(fullname, os.path.join(api_path, '__init__.py')),
                        is_package=True
                    )
            # For submodules like 'api.serper_api'
            else:
                submodule = fullname.split('.')[-1]
                api_path = os.path.join(project_root, 'src', 'api', f"{submodule}.py")
                if os.path.exists(api_path):
                    return importlib.machinery.ModuleSpec(
                        name=fullname,
                        loader=importlib.machinery.SourceFileLoader(fullname, api_path),
                        is_package=False
                    )
        return None

# Install the custom finder at the beginning of sys.meta_path
sys.meta_path.insert(0, ApiImportFinder()) 