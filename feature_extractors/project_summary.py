from typing import Dict, Any, List

def _get_filename_from_path(path: str) -> str:
	"""
	Извлекает имя файла из пути.
	"""
	return path.split('/')[-1]

def is_monorepository(file_paths: List[str]) -> bool:
	"""
	Проверяет, используется ли монорепозиторий.
	"""
	# Проверяем, есть ли несколько проектов в корне репозитория
	project_dirs = [item for item in file_paths if _get_filename_from_path(item) not in ['.git', '.gitignore', 'README.md']]
	return len(project_dirs) > 1

def is_have_gitignore_file(file_paths: List[str]) -> bool:
	"""
	Проверяет наличие файла .gitignore в корне проекта.
	"""
	return '.gitignore' in [ _get_filename_from_path(item) for item in file_paths ]

def is_have_editorconfig_file(file_paths: List[str]) -> bool:
	"""
	Проверяет наличие файла .editorconfig в корне проекта.
	"""
	return '.editorconfig' in [ _get_filename_from_path(item) for item in file_paths ]

def is_have_gitattributes_file(file_paths: List[str]) -> bool:
	"""
	Проверяет наличие файла .gitattributes в корне проекта.
	"""
	return '.gitattributes' in [ _get_filename_from_path(item) for item in file_paths ]

def is_have_deployment_files(file_paths: List[str]) -> bool:
	"""
	Проверяет наличие файлов для CI/CD в каталоге deployment.
	"""
	return any('deployment' in path.split('/') for path in file_paths)

def is_have_docs_directory(file_paths: List[str]) -> bool:
	"""
	Проверяет наличие технической документации в каталоге docs.
	"""
	docs_files = [path for path in file_paths if 'docs/' in path]
	return len(docs_files) > 0

def is_have_plantuml_diagrams(file_paths: List[str]) -> bool:
	"""
	Проверяет наличие диаграмм PlantUML в документации.
	"""
	docs_files = [path for path in file_paths if 'docs/' in path]
	for file_name in docs_files:
		if file_name.endswith('.puml') or file_name.endswith('.plantuml'):
			return True
	return False

def is_have_source_code_directory(file_paths: List[str]) -> bool:
	"""
	Проверяет, что каталог с исходным кодом имеет лаконичное имя.
	"""
	source_dirs = ['src/', 'app/', 'backend/']
	return any(dir_name in path for dir_name in source_dirs for path in file_paths)

def is_have_formatter_configs(file_paths: List[str]) -> bool:
	"""
	Проверяет наличие конфигурационных файлов для yapf и isort.
	"""
	configs = ['.style.yapf', 'setup.cfg', 'pyproject.toml', 'tox.ini']
	return any(config in path for config in configs for path in file_paths)

def is_have_jwt_authorization(component_imports: Dict[str, List[str]]) -> bool:
	"""
	Проверяет реализацию авторизации с использованием JWT и PyJWT.
	"""
	for imports in component_imports.values():
		if 'jwt' in imports or 'PyJWT' in imports:
			return True
	return False

def is_have_swagger_endpoint(component_imports: Dict[str, List[str]], file_paths: List[str]) -> bool:
	"""
	Проверяет наличие использования Swagger в проекте по файлам и импортам.
	"""
	# Проверяем наличие файлов, связанных с Swagger
	swagger_files = ['swagger.yaml', 'swagger.json']
	if any(file in file_paths for file in swagger_files):
		return True

	# Проверяем наличие импортов, связанных с Swagger и FastAPI
	swagger_imports = ['flask_swagger', 'drf_yasg', 'swagger_ui', 'fastapi', 'fastapi.openapi', 'fastapi.openapi.utils']
	for imports in component_imports.values():
		if any(swagger_import in imports for swagger_import in swagger_imports):
			return True

	return False
