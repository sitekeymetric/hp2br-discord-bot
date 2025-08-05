source .venv/bin/activate
uv pip install --requirements requirements.txt
uvicorn main:app --reload
