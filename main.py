from bot import create_app
import config

# pylint: disable=C0103
app = create_app(config)
# pylint: enable=C0103

# This is only used when running locally
if __name__ == '__main__':
    app.run()
