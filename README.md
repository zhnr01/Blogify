
# 📝 Flask Blogging Platform

A full-featured blogging website built with [Flask](https://flask.palletsprojects.com/), inspired by Miguel Grinberg's Flask Mega-Tutorial.  
Currently a work-in-progress 🚧 — APIs and some bug fixes are still pending.

## 🚀 Features (Implemented So Far)

- User registration and login
- Post creation, editing, and deletion
- User profile pages
- Pagination for blog posts
- Comment system (if applicable)
- Form handling with WTForms
- Database integration with SQLAlchemy
- Bootstrap for responsive UI

## 🔧 Work In Progress

- RESTful API for posts and users
- Bug fixes (form validation, edge cases, etc.)
- Unit testing

## 🛠️ Tech Stack

- Python 3.x
- Flask
- Flask-SQLAlchemy
- Flask-Migrate
- Flask-Login
- WTForms
- Jinja2
- Bootstrap

## 📦 Installation

```bash
git clone https://github.com/Zeeshan-R9/Blogging-site.git
cd Blogging-site
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
flask db upgrade
flask run
````

## 💡 To-Do

* [ ] Build REST APIs for posts/users
* [ ] Fix known bugs
* [ ] Add automated tests
* [ ] Improve mobile UI
* [ ] Prepare for deployment (Heroku/Docker/etc.)

## 🙌 Contribution

PRs and feedback are welcome!
Feel free to fork and submit suggestions for improvements.

## 📄 License

This project is licensed under the MIT License.

---
