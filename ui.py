#!/usr/bin/env python3

import streamlit as st
import time
import zipfile
import os
import shutil
from pathlib import Path
from analytics import apply_analytics
from uuid import uuid4
import tempfile
from zipfile import ZipFile 
from xhtml2pdf import pisa


def convert_html_to_pdf(html_string, pdf_path):
    with open(pdf_path, "wb") as pdf_file:
        pisa_status = pisa.CreatePDF(html_string, dest=pdf_file)
        
    return not pisa_status.err

# Streamlit App
def main():
	st.title("Code Analysis Tool")
	st.write("Upload a ZIP archive for analysis.")

	# File uploader
	uploaded_file = st.file_uploader("Drag and drop your ZIP file here", type=["zip"])

	if uploaded_file:
		# Save uploaded file
		#zip_path = temp_dir / uploaded_file.name
		with tempfile.TemporaryDirectory() as temp_dir:
			zip_path = os.path.join(temp_dir, uploaded_file.name)
			with open(zip_path, "wb") as f:
				f.write(uploaded_file.read())
		
			# Check if the uploaded file is a valid ZIP
			if zipfile.is_zipfile(zip_path):
				st.success("File uploaded successfully! Starting analysis...")
				
				# Show progress bar
				progress_bar = st.progress(0)
				progress_bar.progress(10)

				source_path = temp_dir + "/" + uploaded_file.name + '.dir'
				os.makedirs(source_path, exist_ok=True)
				with ZipFile(zip_path, 'r') as zObject:
					zObject.extractall(path=source_path)

				# Perform analysis
				report = apply_analytics(source_path)
				report_path = f"static/{uuid4()}.html"

				#if not convert_html_to_pdf(report, report_path):
				#	st.error("Failed to convert HTML to PDF. Please try again.")
				with open(report_path, "w") as report_file:
					report_file.write(report)
				progress_bar.progress(100)

				# Provide a link to the report
				st.success("Analysis completed!")
				st.link_button("Download your report", f"http://localhost:9000/{report_path.replace('static/', '')}")
			else:
				st.error("The uploaded file is not a valid ZIP archive. Please try again.")

if __name__ == "__main__":
	main()
