source .venv/bin/activate
pip install --requirements requirements.txt
uvicorn main:app --reload
