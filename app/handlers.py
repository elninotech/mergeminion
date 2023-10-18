from typing import Dict, Optional, Awaitable
from slack_sdk.errors import SlackApiError
from app import client
from app.models import *
from async_lru import alru_cache
from app import config
import logging


async def handle_mr_notify(data: Dict, channel_name: str):
    """
    The handle_mr_notify function is the main function that handles all merge request webhooks.
    It first checks if the object_kind is a merge_request, and then checks if it's a draft MR.
    If it's not either of those, then we know that this is an open or update MR event.

    :param data: Dict: Get the data from the webhook
    :param channel_name: str: Determine which channel to send the message to
    :return: None
    """
    if data.get('object_kind', '') != "merge_request":
        raise ValueError(f"Enable MR webhook on project: {parser.deep_get(data, 'project.web_url')}")

    title = parser.deep_get(data, "object_attributes.title")
    username = data.get('user').get('username', '')

    # Do not notify in slack if draft MR
    if config.EXCLUDE_DRAFT and parser.is_draft(title):
        raise ValueError("Draft MR, no slack update will be sent")

    action =  parser.deep_get(data, "object_attributes.action")
    channel_id = parser.get_channel_id(channel_name)

    # Check if a Draft has been marked ready
    is_ready = False
    if config.NOTIFY_WHEN_MR_READY:
        is_ready = parser.is_ready(action, data.get('changes', ''))

    user_list = await get_users_list()
    parser.set_user_list(user_list)

    if action == 'open' or is_ready:
        user_id = parser.parse_username_to_slack_id(username)
        await send_new_msg(data, channel_id, user_id, is_ready)
    else:
        await send_upd_msg(data, channel_id, username)


async def send_new_msg(data: Dict, channel_id: str, user_id: str, is_ready: bool):
    """
    The send_new_msg function is used to send a new message to the channel.

    :param is_ready: bool: Draft marked as Ready
    :param user_id: str: Slack user ID
    :param data: Dict: Pass in the data from the webhook
    :param channel_id: str: Specify the channel to send the message to
    :return: None
    """
    try:
        response = await client.chat_postMessage(channel=channel_id,
                                                 blocks=parser.parse_request_to_nm_blocks(data, user_id, is_ready),
                                                 metadata=parser.parse_request_to_nm_metadata(data),
                                                 unfurl_links=False,
                                                 text='')
        assert response["ok"] is True
        logging.info("Bot posted new message to the channel. Clearing channel history cache.")
        get_message_history.cache_clear()
    except SlackApiError as e:
        assert e.response['ok'] is False
        assert e.response["error"]
        raise e


async def send_upd_msg(data, channel_id, username):
    """
    The send_upd_msg function is responsible for sending the update message to Slack, as well as updating thread start.

    :param data: Dict: Pass in the data from the webhook
    :param channel_id: str: Specify the channel to send the message to
    :param username: str: Slack username
    :return: None
    """
    message_history = await get_message_history(channel_id)
    history_thread = parser.get_thread_start(data, message_history)

    if history_thread is None:
        raise ValueError("Thread not found")

    thread = Thread(history_thread, data)
    update_type = thread.get_update_type()
    assignee_list = [thread.old_assignees, thread.old_reviewers, thread.get_assignees(), thread.get_reviewers()]
    action = parser.deep_get(data, "object_attributes.action")
    if (update_type != '' and action == 'update') or action != 'update':
        try:
            response = await client.chat_postMessage(channel=channel_id,
                                                     blocks=parser.parse_request_to_um_blocks(username, update_type,
                                                                                              assignee_list),
                                                     metadata=parser.parse_request_to_um_metadata(data),
                                                     thread_ts=thread.ts,
                                                     unfurl_links=False,
                                                     text='')
            assert response["ok"] is True
        except SlackApiError as e:
            assert e.response['ok'] is False
            assert e.response["error"]
            raise e

    try:
        response = await client.chat_update(channel=channel_id,
                                            ts=thread.ts,
                                            blocks=thread.blocks,
                                            metadata=thread.metadata,
                                            text=thread.text)
        assert response["ok"] is True
    except SlackApiError as e:
        assert e.response['ok'] is False
        assert e.response["error"]
        raise e


@alru_cache(maxsize=10, ttl=None)
async def get_message_history(channel: str) -> Awaitable[Dict]:
    """
    The get_message_history function takes a channel ID as an argument and returns the last 100 messages in that channel.

    :param channel: str: Specify the channel to get the message history from
    :return: A dictionary of messages
    """
    try:
        response = await client.conversations_history(channel=channel,
                                                      limit=100,
                                                      include_all_metadata=True)
        assert response['ok'] is True
        return response['messages']
    except SlackApiError as e:
        assert e.response['ok'] is False
        assert e.response["error"]
        raise e


@alru_cache(maxsize=1, ttl=None)
async def get_users_list() -> Awaitable[list]:
    """
    The get_users_list function returns a list of all users in the workspace.

    :return: A list of all the users in your workspace
    """
    try:
        response = await client.users_list()

        assert response['ok'] is True
        return response['members']
    except SlackApiError as e:
        assert e.response['ok'] is False
        assert e.response["error"]
        raise e
