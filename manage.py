import os
from app import create_app, db
from app.models import Post, User, Role
from flask_migrate import Migrate


app = create_app(os.getenv('FLASK_CONFIG') or 'default')
migrate = Migrate(app, db)


'''
    The app is automatically imported and used as 'app', so there is no need to specify it here.
'''
@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Role=Role)


@app.cli.command('test')
def test():
    """Run the unit tests."""
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)

@app.cli.command('delete_records')
def delete_records():
    for user in User.query.all():
        db.session.delete(user)
    for post in Post.query.all():
        db.session.delete(post)
    db.session.commit()
    
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)

