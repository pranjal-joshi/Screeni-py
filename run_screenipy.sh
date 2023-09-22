#!/bin/bash
variable_name="SCREENIPY_GUI"

cd src

if [ -z "${!variable_name}" ]; then
	python3 screenipy.py
else
	streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0
fi