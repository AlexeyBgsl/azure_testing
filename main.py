from bot import create_app
import config

app = create_app(config)

# This is only used when running locally
if __name__ == '__main__':
    app.run()
