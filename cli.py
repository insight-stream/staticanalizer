#!/usr/bin/env python3

import uuid
import glob
import os
import sys
from zipfile import ZipFile 
from pyunpack import Archive
from tempfile import TemporaryDirectory
import json
from analytics import apply_analytics


def unpack_zip(zip_file_path: str, output_dir: str):
	with ZipFile(zip_file_path, 'r') as zObject:
		zObject.extractall(path=output_dir)
	return output_dir

def unpack_7z(zip_file_path: str, output_dir: str):
	Archive(zip_file_path).extractall(output_dir)
	return output_dir

def extract_projects(dir_path: str):
	for project_archive in glob.glob(f"{dir_path}/**/*.zip") + glob.glob(f"{dir_path}/*.zip"):
		with TemporaryDirectory() as temp_dir:
			yield project_archive, unpack_zip(project_archive, temp_dir)

	for project_archive in glob.glob(f"{dir_path}/**/*.7z") + glob.glob(f"{dir_path}/*.7z"):
		with TemporaryDirectory() as temp_dir:
			yield project_archive, unpack_7z(project_archive, temp_dir)


if __name__ == "__main__":
	for project_archive, project_dir in extract_projects(sys.argv[1]):
		print(project_archive)
		print(json.dumps(apply_analytics(project_dir), indent=4, ensure_ascii=False))
		print()
