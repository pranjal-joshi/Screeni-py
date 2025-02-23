#!/bin/bash
variable_name="SCREENIPY_GUI"

cd src

# Check if the script was provided with at least one argument
if [ $# -lt 1 ]; then
    echo "Usage: $0 [--gui|--cli]"
    exit 1
fi

# Check the value of the first argument
if [ "$1" = "--gui" ]; then
	export SCREENIPY_GUI=TRUE
	echo " "
    echo "Starting in GUI mode... Copy and Paste following URL in your browser.."
	streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0
elif [ "$1" = "--cli" ]; then
	unset "SCREENIPY_GUI"
    echo "Starting in CLI mode..."
    python3 screenipy.py
else
    echo "Invalid argument. Usage: $0 [--gui|--cli]"
    exit 1
fi
