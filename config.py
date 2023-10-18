import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
    SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
    SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
    TEAM_CHANNEL_MAPPING = eval(os.environ.get("TEAM_CHANNEL_MAPPING"))
    GITLAB_WEBHOOK_TOKEN = os.environ.get("GITLAB_WEBHOOK_TOKEN")
    SLACK_GITLAB_USER_MAPPING = eval(os.environ.get("SLACK_GITLAB_USER_MAPPING"))
    EXCLUDE_DRAFT = os.environ.get("EXCLUDE_DRAFT")
    NOTIFY_WHEN_MR_READY = os.environ.get("NOTIFY_WHEN_MR_READY")
    BOT_URL = os.environ.get("BOT_WEBHOOK_URL")
    BOT_NAME = os.environ.get("BOT_NAME")
    GITLAB_GROUP_ID_MAPPING = eval(os.environ.get("GITLAB_GROUP_ID_MAPPING"))
    ACCESS_GITLAB = os.environ.get("ACCESS_GITLAB")
