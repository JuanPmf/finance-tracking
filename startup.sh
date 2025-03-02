#!/bin/bash
pip install -r requirements.txt
streamlit run main.py --server.port=8080 --server.address=0.0.0.0

