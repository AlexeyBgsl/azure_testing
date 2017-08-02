from bot import create_app
import config

app = create_app(config)

# Make the WSGI interface available at the top level so wfastcgi can get it.
wsgi_app = app.wsgi_app

# This is only used when running locally
if __name__ == '__main__':
    app.run()
