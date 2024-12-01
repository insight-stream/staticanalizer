#!/usr/bin/env python3

from typing import List, Union, Optional, Dict, Any, Tuple, Callable, defaultdict, Set
from directory_tree import DisplayTree
from typing import Optional
import glob
import os
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
import json
import ast
import inspect
import sys
import os
import importlib
import pkgutil
import markdown
from jinja2 import Environment, FileSystemLoader
from graphviz import Digraph, Graph
from uuid import uuid4
import tempfile
import base64


COMPRESSA_API_DEMO_KEY = os.getenv('COMPRESSA_KEY')
llm = ChatOpenAI(
		openai_api_key=COMPRESSA_API_DEMO_KEY, 
		model="Compressa-Qwen2.5-14B-Instruct",
		temperature=0,
		openai_api_base='https://api.qdrant.mil-team.ru/chat-1/v1',
		max_retries=3,
		request_timeout=120,
		max_tokens=10000,
	)


def _project_files(path) -> str:
	return DisplayTree(path, stringRep=True, showHidden=True)

def _parse_file_tree(path: str) -> Dict[str, List[str]]:
	return [ i.replace(path + '/', '') for i in glob.glob(path + '/**', recursive=True) if os.path.isfile(i) ]

def _project_readmes(path) -> Optional[str]:
	txts = []
	basepath = path.split('/')[-1]
	for rp in glob.glob(path + '/**/README*') + glob.glob(path + '/README*'):
		with open(rp, 'r') as f:
			txts.append(rp.replace('/'.join(path.split('/')[0:-1]), '') + ':\n\n' + f.read())
	return '\n\n\n'.join(txts)

def _get_imports_from_file(file_path: str) -> List[str]:
	with open(file_path, 'r') as file:
		try:
			tree = ast.parse(file.read(), filename=file_path)
		except Exception as e:
			print(f"Error parsing file {file_path}: {e}", file=sys.stderr)
			return []
	imports = []
	for node in ast.walk(tree):
		if isinstance(node, ast.Import):
			for alias in node.names:
				imports.append(alias.name)
		elif isinstance(node, ast.ImportFrom):
			if node.module:
				imports.append(node.module)
	return imports

def _get_component_imports(root_path: str, component_base_path: str) -> List[Tuple[str, List[str]]]:
	imports = {}
	for component_path in glob.glob(root_path + '/' + component_base_path + '/**/*.py') + glob.glob(root_path + '/' + component_base_path + '/*.py'):
		if not os.path.isfile(component_path):
			continue
		imports[component_path.replace(root_path + '/', '')] = _get_imports_from_file(component_path)
	return imports

def _build_module_dependencies(component_imports: Dict[str, List[str]], root_dir: str) -> Dict[str, List[str]]:
	"""
	Строит граф зависимостей модулей.
	"""
	module_dependencies = defaultdict(set)
	for file_path, imports in component_imports.items():
		rel_path = os.path.relpath(file_path, root_dir)
		module_name = rel_path.replace('/', '.')[:-3]
		for imported_module in imports:
			module_dependencies[module_name].add(imported_module)
		if len(imports) == 0:
			module_dependencies[module_name] = set([])

	module_dependencies = {module: list(dependencies) for module, dependencies in module_dependencies.items()}

	return module_dependencies

def project_overview_info(path) -> Dict[str, Any]:
	parser = JsonOutputParser()
	file_tree = _project_files(path)
	readmes = _project_readmes(path)

	chain_answ = ChatPromptTemplate.from_template(
		'''THERE IS PROJECT FILE STRUCTURE:

		{file_tree}

THERE ARE README FILES CONTENT:

		{readmes}

Use your knowledge and information above to answer the following questions:

- what is the purpose of the project? Just write a short description, for example: "This project is a web application for managing a company's employees."
- is documentation answers to questions about project structure and deployment (true or false)?
- are there tests in the project (true or false)?
- estimate how well the project is documented. Good if a new developer can understand and deploy the project by documentation, bad if he can't understand the purpose of the project. Write a short and fair description from the point of view of a new developer, for example: "The project does not have appropriate documentation; there are missing parts: ..."
- what build system is used? Just write the name of the system + config location, for example, "CMake (subdir/CMakeLists.txt), Makefile (./Makefile)"
- what is a list of the program components? Use the following rules to determine a component:
	- assume component is a separate process/library/service/deployment unit in runtime.
	- src/ directory usually contains one component.
	- you may determine the component root directory by dependency configs (e.g., project.toml/requirements.txt) or by build system configs (e.g., CMakeLists.txt) in it.
	- auxilary files, like documentation, or migrations, may be moved to the separate component.
- where is a dependency config file (e.g., project.toml/requirements.txt) for each component? Write the path to the file from the project root, for example, "backend/pyproject.toml.".
- what is the path of each component? Use a relative path from the project root, for example, "backend/main.py.".
- what is the purpose of each component?
- what program stack of each component?
- where is an entry point file for each component? If there is no entry point (e.g., the component is library/config/documentation), write null.
- write a critical description of the project architecture for improving the project. Use the following rules:
	- put each point in a separate item of the list. 
	- put only issues, don't write anything else.
	- is there a clear separation between components in the dependency management point of view?
	- is there a clear separation between components in the build system point of view?
	- is there a clear separation between components in the code structure point of view?
	- is there a clear separation between components in the documentation point of view?
	- add your own points of view if you see something important for new developers.

Use the following rules for your answer:

- use following JSON format for your answer: {{ "project_name": "...", "purpose": "...", "build_system": "...", "tests": false|true, "documentation": "...", "components" : [ "dependency_config": "...", "path": "...", "purpose": "...", "stack": "...", "entry_point": "..." ], "architecture_issues": [ "...", "..." ] }}
- if you don't know the answer to the question, put null (without quotes) in the appropriate JSON key.

Your JSON answer:
	'''.strip()) | llm | parser
	
	report = chain_answ.invoke({'file_tree': file_tree, 'readmes': readmes})
	report['project_files'] = _parse_file_tree(path)

	components = []
	for component in report['components']:
		imports = _get_component_imports(path, component['path'])
		import_dependencies_graph = _build_module_dependencies(imports, component['path'])
		component_with_imports = {**component, 'import_dependencies_graph': import_dependencies_graph}
		components.append(component_with_imports)
	report['components'] = components

	return report

def _get_rule_functions(package_path: str) -> List[Callable]:
	"""
	Получает список функций-правил из всех модулей пакета feature_extractors.
	"""

	# Получаем путь к текущему пакету
	package_name = os.path.basename(package_path)

	rule_functions = []

	# Импортируем все модули из пакета
	for _, module_name, _ in pkgutil.iter_modules([package_path]):
		module = importlib.import_module(f"{package_name}.{module_name}")
		
		# Получаем функции из каждого модуля
		functions = inspect.getmembers(module, inspect.isfunction)
		
		# Отбираем функции с одним аргументом file_paths
		module_rules = [f for name, f in functions 
					   if len(inspect.signature(f).parameters) >= 1 
					   and not name.startswith('_')]
		
		rule_functions.extend(module_rules)

	return rule_functions

def _apply_overall_rules(overview: Dict[str, Any], rule_functions: List[Callable]) -> Dict[str, Any]:
	"""
	Применяет все правила из модуля к переданному обзору проекта.
	"""
	project_files = overview['project_files']

	overview['project_properties'] = {}
	# Применяем каждую функцию и сохраняем результат
	for func in rule_functions:
		if len(inspect.signature(func).parameters) == 1 and list(inspect.signature(func).parameters.keys())[0] == 'file_paths':
			rule_name = func.__name__.replace('is_', '')
			overview['project_properties'][rule_name] = func(project_files)

	return overview

from graphviz import Digraph
from typing import Dict, List

from graphviz import Digraph
from typing import Dict, List

def _generate_graphviz_dependencies(component_imports: Dict[str, List[str]], output_dir: str) -> None:
    """
    Generates an SVG image of module dependencies using Graphviz with optimized layout and size constraints.

    :param component_imports: dict - A map of module dependencies in the format {'module': ['dependency1', 'dependency2']}
    :param output_dir: str - The output directory for the generated SVG file.
    :param width: float - The width of the SVG canvas in inches (default is A4 width, 8.27 inches).
    :param height: float - The height of the SVG canvas in inches (default is A4 height, 11.69 inches).
    :return: None - Saves an SVG file.
    """
    # Create a directed graph
    dot = Digraph(format='png')
    
    # Configure graph attributes
    dot.attr(
        rankdir='LR',  # Left-to-right layout
        splines='ortho',  # Orthogonal edges for better readability
        size=f"11.7,8.3",  # Limit canvas size
        ratio="fill"  # Compress to fit within the defined size
    )
    dot.attr('node', shape='box', style='rounded,filled', fillcolor='#f2f2f2', fontname='Arial', fontsize='8')

    # Add nodes and edges
    modules = set(component_imports.keys()) | {dep for deps in component_imports.values() for dep in deps}
    for module in modules:
        dot.node(module)

    for module, dependencies in component_imports.items():
        for dep in dependencies:
            dot.edge(module, dep)

    # Render the graph to SVG
    return dot.render(output_dir + 'graph', format='png')



def _render_plantuml_diagram(component_imports: Dict[str, List[str]]) -> str:
	"""
	Рендерит диаграмму PlantUML в изображение.
	"""

	with tempfile.TemporaryDirectory() as tmpdir:
		graph_svg_path = _generate_graphviz_dependencies(component_imports, tmpdir)
		convert = open(graph_svg_path, 'rb').read()
		convert = base64.b64encode(convert).decode('utf-8')
	return convert

def _apply_component_rules(overview: Dict[str, Any], rule_functions: List[Callable], base_dir: str) -> List[Dict[str, Any]]:
	"""
	Применяет все правила из модуля к переданному списку компонентов.
	"""

	components = overview['components']
	project_files = overview['project_files']

	for component in components:
		component['architecture_notes'] = {}
		imports = component['import_dependencies_graph']
		for func in rule_functions:
			if list(inspect.signature(func).parameters.keys())[0] == 'component_imports':
				rule_name = func.__name__.replace('is_', '')
				# TODO: invent a better way to handle tricky rules
				if len(inspect.signature(func).parameters) == 2:
					if 'hexagonal_architecture' in rule_name:
						component['architecture_notes'][rule_name] = func(imports, component['path'])
					else:
						component[rule_name] = func(imports, project_files)
				elif len(inspect.signature(func).parameters) == 1:
					component[rule_name] = func(imports)
				elif len(inspect.signature(func).parameters) == 3:
					component[rule_name] = func(imports, base_dir + '/' + component['path'], llm)

	overview['components'] = components
	return overview


def _raw_analytics(path):
	overview = project_overview_info(path)

	rule_functions = _get_rule_functions('./feature_extractors')
	overview = _apply_overall_rules(overview, rule_functions)
	overview = _apply_component_rules(overview, rule_functions, path)

	overview['project_files'] = [ f.replace(path + '/', '') for f in overview['project_files'] ]
	return overview

def apply_analytics(path):
	overview = _raw_analytics(path)
	
	fowler_prompt = ChatPromptTemplate.from_template(
		'''
You are Martin Fowler, a famous software architect. Your task is to write a review of the project principles of architecture based on the JSON description.
You should use the following rules:

- write a short review (at most 3 paragraphs) of the project principles of architecture in markdown format.
- focus on the layers and components.
- determinate the main architecture patterns used in the project (for logic, data, presentation layers, etc.).
- write a short description of each pattern.
- write comments to improve the project architecture.
- add module names and other details as proofs of your words.
- write your report for the project manager.
- use rude language in your report.
- be brief and concise.
- without mincing words, let bad programmers know their place!
- Use Russian language for your answer.

After that, measure the project maintainability and a code smell based on the architecture (1 — the unmaintainable crap, 5—perfect).
Put your answer in the following JSON format: {{ "summary": "...markdown text...", "maintainability": 1|2|3|4|5 }}

Project description:

{json_description}

JSON ответ:
		'''.strip()) | llm | JsonOutputParser()

	pepe_prompt = ChatPromptTemplate.from_template(
		'''
You are Pepe, a typical Russian developer. Your task is to write a review of the project maintainability and build system based on the JSON description.
You should use the following rules:

- write a short review (at most 3 paragraphs) of the project maintainability and build system in markdown format.
- focus on project size and complexity.
- pay attention to the "project_properties" section: this section contains some metrics of maintainability.
- pay attention to the documentation and tests: you are interested in fast dive into the project through documentation and tests.
- note a fact of overdesign if it is present.
- what a build system is used?
- you prefer simple and stupid solutions.
- your prefer small independed components in the project.
- your admire Unix philosophy, analyze project structure and components in the Unix point of view.
- write your report for the developer leader.
- use passive-aggressive voice in your report.
- Use Russian language for your answer.

After that, measure the project maintainability and simplicity based on your comments (1 — the unmaintainable crap, 5 - very simple and stupid).
Put your answer in the following JSON format: {{ "summary": "...markdown text...", "maintainability": 1|2|3|4|5 }}

Project description:

{json_description}

JSON ответ:
		'''.strip()) | llm | JsonOutputParser()

	fowler_summary = fowler_prompt.invoke({'json_description': json.dumps(overview, ensure_ascii=False, indent=4)})
	pepe_summary = pepe_prompt.invoke({'json_description': json.dumps(overview, ensure_ascii=False, indent=4)})
	
	desc = {
		"project_name": overview['project_name'],
		"project_issues": overview.get('architecture_issues', []),
		"architect": {
			"review": markdown.markdown(fowler_summary['summary']),
			"evaluation": fowler_summary['maintainability'],
		},
		"developer": {
			"review": markdown.markdown(pepe_summary['summary']),
			"evaluation": pepe_summary['maintainability'],
		},
		"project_summary": overview['project_properties'],
		"components": [ {
			"name": c['path'],
			"structure_diagram": _render_plantuml_diagram(c['import_dependencies_graph']),
			"summary": c['purpose'],
			"stack": c['stack'],
			"patterns":  list({ i["pattern"] for i in c["check_data_layer"] }),
			"issues": dict([ ((i["issue"] + " " + i["location"]), i["how_to_fix"]) for i in c.get('issues', []) ] + [ ("Поддержка Swagger документации", c['have_swagger_endpoint']), ("Поддержка JWT-авторизации", c['have_jwt_authorization']) ]),
		} for c in overview['components'] ],
	}

	env = Environment(loader=FileSystemLoader('.'))
	template = env.get_template('report_template.html')
	output_html = template.render(desc)

	return output_html

if __name__ == "__main__":
	print(apply_analytics(sys.argv[1]))
