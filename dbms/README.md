export FLASK_APP=dbms.app
export FLASK_ENV=development
export FLASK_DEBUG=1

python -m pytest dbms/test.py
