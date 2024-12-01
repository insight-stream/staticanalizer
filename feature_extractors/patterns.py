import os
from typing import Dict, List, Optional


def _get_layer_modules(component_imports: Dict[str, List[str]], root_dir: str) -> Dict[str, str]:
	"""
	Получает словарь, сопоставляющий модули с их слоями.
	"""
	# Определяем слои и соответствующие им директории
	layer_dirs = {
		'domain': ['domain', 'core', 'model', 'entities'],
		'application': ['application', 'service', 'use_cases', 'services'],
		'adapters': ['adapters', 'infrastructure', 'interfaces', 'ports'],
		'config': ['config', 'settings', 'composites']
	}

	module_layers = {}

	# Сопоставляем файлы модулям и классифицируем их по слоям
	for module_name, imports in component_imports.items():
		file_path = module_name.replace('.', os.sep) + '.py'
		# Определяем слой модуля
		rel_path = os.path.relpath(file_path, root_dir)
		layer = None
		for layer_name, dirs in layer_dirs.items():
			if any(dir_name in rel_path.split(os.sep) for dir_name in dirs):
				layer = layer_name
				break
		if not layer:
			# Если модуль не соответствует ни одному слою, присваиваем ему 'other'
			layer = 'other'

		module_layers[module_name] = layer

	return module_layers


def hexagonal_architecture_comments(component_imports: Dict[str, List[str]], root_dir: str) -> List[str]:
	"""
	Проверяет, построен ли проект по принципам гексагональной архитектуры.

	Параметры:
	- project_files: список путей к файлам проекта.
	- file_imports: словарь, сопоставляющий пути файлов со списком импортов в каждом файле.
	  Формат: { 'path/to/module.py': ['imported.module1', 'imported.module2'], ... }
	- root_dir: корневая директория проекта.

	Возвращает:
	- True, если проект соответствует принципам гексагональной архитектуры, иначе False.
	"""

	module_layers = _get_layer_modules(component_imports, root_dir)
	# Анализируем зависимости
	hex_architecture_errors = []
	is_hexagonal_architecture_threats = 'domain' in module_layers.values() and 'application' in module_layers.values() and 'adapters' in module_layers.values()
	for module, imports in component_imports.items():
		module_layer = module_layers.get(module, 'other')
		for imported_module in imports:
			imported_layer = module_layers.get(imported_module, 'other')
			if module_layer == 'domain':
				if imported_layer in ['application', 'adapters', 'config']:
					# Модуль доменного слоя зависит от внешнего слоя
					hex_architecture_errors.append(f"Hexagonal Architecture Violation: domain module '{module}' depends on '{imported_module}' from layer '{imported_layer}'")
					
	return hex_architecture_errors if is_hexagonal_architecture_threats else []

