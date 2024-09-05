import secrets
from flask import Flask

def create_app(testing=False, commit=True):
    '''
    Application factory function
    '''
    # create and configure the app
    app = Flask(__name__, instance_relative_config=False)
    app.config['SECRET_KEY'] = secrets.token_hex()
    app.config['TESTING'] = testing
    app.config['COMMIT'] = commit

    # a simple page that says hello
    @app.route('/hello')
    def hello():
        return 'Hello, World!'

    with app.app_context(): # Prevents a "RuntimeError: Working outside of application context."
        from . import db # Register commands and functions with applicaton instance
    db.init_app(app)
    
    from . import bp # import and register the blueprint
    app.register_blueprint(bp.bp)

    return app
