# Octopus Electroverse - Tech Task

### Prerequisites

### Examples

- Rebuild and re-run the application in detached mode: `make up ARGS="--build --detach"`
- Running a specific test file: `make test ARGS="path/to/test.py"`
- Running tests matching a keyword: `make test ARGS="-k test_specific_test_case"`

## Local Development (SQLite)
This project is configured to run locally with SQLite for ease of setup.

### Install dependencies
```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Initialize database
```
python manage.py migrate
```

### Load data
```
python manage.py load_integrated --path integrated.json --reset
```

### Run the server
```
python manage.py runserver
```

### API endpoints
- List locations: http://127.0.0.1:8000/task/
- Location detail: http://127.0.0.1:8000/task/<location_reference>/

### Admin
```
python manage.py createsuperuser
```
Then visit http://127.0.0.1:8000/admin/

### Tests
```
$env:PYTHONPATH="."
python manage.py test src.task.tests
```

## Notes
- Source data comes from Open Charge Map and is converted to integrated.json via scripts/ocm_to_integrated.py.
- The API is a simple REST JSON interface using plain Django views.
