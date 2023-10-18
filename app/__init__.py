import logging
from flask import Flask
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.http_retry.builtin_async_handlers import AsyncRateLimitErrorRetryHandler
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt import App
from config import Config

config = Config()
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
client = AsyncWebClient(token=config.SLACK_BOT_TOKEN)
rate_limit_handler = AsyncRateLimitErrorRetryHandler(max_retry_count=1)
client.retry_handlers.append(rate_limit_handler)
bolt_app = App(token=config.SLACK_BOT_TOKEN,
               signing_secret=config.SLACK_SIGNING_SECRET)
handler = SocketModeHandler(bolt_app, config.SLACK_APP_TOKEN)
handler.connect()


def create_app(config_class: Config):
    app.config.from_object(config_class)
    app.url_map.strict_slashes = False

    with app.app_context():
        from . import routes
        return app
