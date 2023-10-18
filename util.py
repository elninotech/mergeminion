import gitlab
import requests
import os
from typing import Optional


config_file = os.path.expanduser("python-gitlab.cfg")

def get_gitlab(config_name: str = "elnino") -> gitlab.Gitlab:
    # Follow the python-gitlab configuration and name one of the configs "team"
    # https://python-gitlab.readthedocs.io/en/stable/cli-usage.html#configuration-file-format
    # And see python-gitlab.cfg.example
    return gitlab.Gitlab.from_config(config_name, [config_file])

def get_gitlab_requests(type: str, path, data={}):
    config = gitlab.config.GitlabConfigParser("team", [config_file])
    url = f"{config.url}/api/v{config.api_version}{path}"
    headers = {
            'Accept': 'application/json',
            "PRIVATE-TOKEN": config.private_token
            }
    return requests.request(type, url, headers=headers, data=data)

class ConfigInvalidException(Exception):
    "Config items are invalid"
    pass

class Config():
    webhook_token: Optional[str] = os.environ.get("GITLAB_WEBHOOK_TOKEN")

def get_config():
    config = Config()
    return config

def get_webhook_token() -> str:
    config = get_config()
    if config.webhook_token is None:
        raise ConfigInvalidException
    return config.webhook_token
