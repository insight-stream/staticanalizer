from typing import Optional, List, Dict
import os
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser


def check_data_layer(component_imports: Dict[str, List[str]], base_dir: str, llm: ChatOpenAI) -> Optional[List[str]]:
	db_files_pr = ChatPromptTemplate.from_template('''
Your task is to find modules that are responsible for data access on the code of the service (datalayer). 
Use the following format (JSON) for the answer:

["module1", "module2", ...]

There are python project import map (key is a module name, value is a list of imported modules):

{component_imports}

---

Your JSON list:
	'''.strip()) | llm | JsonOutputParser()

	modules = db_files_pr.invoke({'component_imports': component_imports})
	files = [os.path.join(base_dir, module.replace('.', '/') + '.py') for module in modules]

	file_analysis_ch = ChatPromptTemplate.from_template('''
Your task is to analyze the content of the file by the following criteria:

- what datasource types are used in the file.
- does the file use some pattern for organizing data access code (Unit of Work, Repository, ORM, Active Record, etc.).
- are there some errors, warnings or other issues with the code? 
- Give a brief description of the each issue (with information where issue is located) and how to fix it. 
- escape quotes and curly brackets in the answer - you should return valid JSON!
- if there are no data access code in the file, just return empty issues list.

Use the following format for the answer (JSON):

{{
	"file_path": "{file_path}",
	"datasource_types": ["type1", "type2", ...],
	"pattern": "pattern1" | "pattern2" | null,
	"issues": [ {{ "description": "issue1_description", "location": "issue1_location", "how_to_fix": "issue1_how_to_fix" }}, {{ "description": "issue2_description", "location": "issue2_location", "how_to_fix": "issue2_how_to_fix" }}, ...]
}}

File content:

{file_path}:

{file_content}

----

Your JSON answer:
	'''.strip()) | llm | JsonOutputParser()

	analyses = []
	for file in files:
		if not os.path.exists(file):
			continue
		with open(file, 'r') as f:
			content = f.read()
			analysis = file_analysis_ch.invoke({'file_path': file, 'file_content': content[:10000]})
			analyses.append(analysis)
	return analyses
