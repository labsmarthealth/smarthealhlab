<<<<<<< HEAD
# SmartLab Backend Starter (Flask)

This is a minimal Flask backend with:
- User login (Flask-Login, password hashing)
- Protected dashboard route

## 1) Prerequisites
- Python 3.10+

## 2) Setup (Windows PowerShell)
```powershell
cd smartlab_backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## 3) Setup (macOS/Linux)
```bash
cd smartlab_backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 4) Configure environment
Create a file named `.env` in the project root:
```env
SECRET_KEY=change-this-to-a-long-random-string
FLASK_DEBUG=1
```

## 5) Initialize the database and create an admin
```bash
# make sure the venv is active
flask --app app.py db-init
flask --app app.py create-admin
```
The `create-admin` command will ask you for a username and password. 

## 6) Run the server
```bash
flask --app app.py run
# Open http://127.0.0.1:5000/login
```

## 7) Customize UI
- Put your CSS in `static/css/styles.css` or replace the template HTML with your own.
- Update `templates/login.html` and `templates/dashboard.html` with your front-end.

## Notes
- Database: SQLite file `smartlab.db` in the project root.
- To logout, click "Logout" in the top-right of the dashboard.
=======
# smarthealhlab
Flask backend for SmartHealLab
>>>>>>> c9e9c8cdf9b549bdf543989b89c34420b6280518
