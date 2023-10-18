from flask import current_app as app
from flask import request, make_response, Response
import app.handlers as handlers
from slack_sdk.errors import SlackApiError
from app import bolt_app, config
import logging
from typing import Dict


@app.route("/mr/notify", methods=["POST"])
async def send_message() -> Response:
    """
    The send_message function is a ReST endpoint that accepts POST requests from GitLab.
    It will parse the request and send a message to Slack with the relevant information.

    :return: Flask response
    """
    disable_auth = False
    if not config.GITLAB_WEBHOOK_TOKEN:
        disable_auth = True
    gl_token = request.headers.get("X-Gitlab-Token")
    if not disable_auth and (not gl_token or gl_token != config.GITLAB_WEBHOOK_TOKEN):
        return make_response("Add the correct gitlab token to the webhook", 403)

    channel_name = request.args.get('channel', '')
    data = request.json
    try:
        await handlers.handle_mr_notify(data, channel_name)
        return make_response("", 200)
    except SlackApiError as e:
        code = e.response["error"]
        logging.error(e)
        return make_response(f"Failed to send message due to {code}", 200)
    except ValueError as ve:
        logging.error(ve)
        return make_response("Failed to send message due to a ValueError. Please check the logs", 400)


@app.route("/health", methods=["GET"])
def health() -> Response:
    # TODO: If necessary check whether dependencies (e.g. slack, db) are ready for conn.
    """
    The health function is used to check whether the service is up and running.
    :return: Flask response
    """
    return make_response("All OK", 200)


@bolt_app.event('team_join')
def clear_user_cache() -> None:
    """
    The clear_user_cache function is a decorator that clears the cache of the get_users_list function.

    :return: None
    """
    logging.info("Somebody joined teh team! Clearing user list cache.")
    handlers.get_users_list.cache_clear()


@bolt_app.event('user_change')
def clear_if_needed(event: Dict) -> None:
    """
    The clear_if_needed function is a decorator that will clear the cache of the get_users_list function if
    the user who triggered this event has been deleted.

    :param event: Dict: Event data
    :return: None
    """
    usr = event.get('user')
    if usr.get('deleted') is True:
        logging.info("User " + usr.get('username', '') + " was deleted. Clearing user list cache.")
        handlers.get_users_list.cache_clear()
