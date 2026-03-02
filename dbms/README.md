export FLASK_APP=dbms
export FLASK_ENV=development
export FLASK_DEBUG=1

flask init-db
flask populate-db
flask run

# To run the static code analysis

Run the following command in your terminal:

```bash
flake8 .
```