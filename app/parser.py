from dateutil import parser
from flask import request
from typing import Optional, Dict
from app import config
from functools import reduce

DRAFT_SUBSTR = ["WIP", "Draft"]
STATUS_REVIEWING = ":mag: reviewing :mag:"
STATUS_ASSIGNED = ":technologist: assigned :technologist:"
STATUS_OPENED = ":eyes: opened :eyes:"
STATUS_REOPENED = ":repeat: reopened :repeat:"
STATUS_NEW = ":weewoo: new :weewoo:"
STATUS_MERGED = ":rocket: merged :rocket:"
STATUS_CLOSED = ":headstone: closed :headstone:"
STATUS_APPROVED = ":thumbsup: approved :thumbsup:"
STATUS_UNAPPROVED = ":thumbsdown: unapproved :thumbsdown:"

slack_user_list = []


def parse_users_to_string(is_change: bool, user_type: str) -> str:
    """
    Parse assignees or reviewers to a string of usernames

    :param is_change: bool: has user list updated
    :param user_type: str: reviewer or assignee
    :return: A string of users: @username, @username
    """
    current = []

    try:
        if is_change:
            for user in deep_get(request.json, "changes." + user_type + ".current"):
                current.append('<@' + parse_username_to_slack_id(user.get('username')) + '>')
        else:
            raw = request.json.get(user_type, '')
            for i in raw:
                current.append('<@' + parse_username_to_slack_id(i.get('username')) + '>')
    except KeyError:
        pass
    except IndexError:
        pass

    return ','.join(map(str, current)) if current else 'None'


def parse_date() -> str:
    """
    Take the date from the GitLab webhook and parses it into a more readable format.

    :return: The date in a format that is more readable
    """
    date = deep_get(request.json, "object_attributes.updated_at")
    return parser.parse(date).strftime("%-d %b %H:%M")


def parse_action_into_status(action: str) -> str:
    """
    Parse the merge request action into a readable status

    :param action: str: status of an MR
    :return: Status for a Slack message
    """
    switcher = {
        "open": STATUS_OPENED,
        "reopen": STATUS_REOPENED,
        "close": STATUS_CLOSED,
        "approved": STATUS_APPROVED,
        "approval": STATUS_APPROVED,
        "unapproved": STATUS_UNAPPROVED,
        "unapproval": STATUS_UNAPPROVED,
        "merge": STATUS_MERGED,
    }
    result = switcher.get(action, "None")
    return result


def parse_update_type_into_status(update_type: str, reviewers: str) -> str:
    """
    Parse the merge request assignee or reviewer change into a readable status

    :param update_type: str: reviewers or assignees changed
    :param reviewers: str: string of reviewers
    :return: Status for a Slack message
    """
    switcher = {
        "assignee_change": STATUS_ASSIGNED if reviewers == 'None' else STATUS_REVIEWING,
        "reviewer_change": STATUS_REVIEWING,
    }
    result = switcher.get(update_type, "None")
    return result


def parse_no_users_into_status(old_status: str, reviewers: str, assignees: str, no_users_type: str) -> str:
    """
    Parse no reviewers or assignees case into a readable status

    :param old_status: str: old message status
    :param reviewers: str: string of reviewers
    :param assignees: str: string of assignees
    :param no_users_type: str: type of case
    :return: Status for a Slack message
    """
    status = STATUS_OPENED
    old_priority = ['approved', 'unapproved', 'merged', 'closed']

    if old_status.split()[2] in old_priority:
        status = old_status
    elif no_users_type == 'no_assignees' and reviewers != 'None':
        status = STATUS_REVIEWING
    elif no_users_type == 'no_reviewers' and assignees != 'None':
        status = STATUS_ASSIGNED

    return status


def parse_action_into_message(update_type: str, assignee_list: []):
    """
    Parse the action from the request object into a message that can be sent to Slack.

    :param update_type: str: MR update type
    :param assignee_list: []: list of old and new assignees and reviewers
    :return: A verb string to be used in Slack message
    """
    action = deep_get(request.json, "object_attributes.action")

    switcher = {
        "open": "opened",
        "close": "closed",
        "approved": "approved",
        "approval": "approved",
        "unapproved": "unapproved",
        "unapproval": "unapproved",
        "merge": "merged",
        "reopen": "reopened",
        "update": f"{parse_update_into_message(update_type, *assignee_list)}"
    }
    result = switcher.get(action, 'Invalid')
    return result


def parse_update_into_message(update_type: str, old_assignees: str, old_reviewers: str, assignees: str,
                              reviewers: str) -> str:
    """
    Parses out who was unassigned from the MR and who was assigned. Then, determine what message should be sent
    based on the update type.

    :param update_type: str: type of MR update
    :param old_assignees: str: old assignees
    :param old_reviewers: str: old reviewers
    :param assignees: str: new assignees
    :param reviewers: str: new reviewers
    :return: A string that is used to build the message sent to Slack
    """
    unassigned_assignees = parse_unassigned(old_assignees, assignees)
    unassigned_reviewers = parse_unassigned(old_reviewers, reviewers)
    assigned_assignees = parse_assigned(old_assignees, assignees)
    assigned_reviewers = parse_assigned(old_reviewers, reviewers)

    if update_type == 'assignee_change' and unassigned_assignees and not assigned_assignees:
        update_type = 'unassigned_assignees'
    elif update_type == 'assignee_change' and assigned_assignees and not unassigned_assignees:
        update_type = 'assigned_assignees'
    elif update_type == 'assignee_change' and assigned_assignees and unassigned_assignees:
        update_type = 'assigned_and_unassigned_assignees'

    if update_type == 'reviewer_change' and unassigned_reviewers and not assigned_reviewers:
        update_type = 'unassigned_reviewers'
    elif update_type == 'reviewer_change' and assigned_reviewers and not unassigned_reviewers:
        update_type = 'assigned_reviewers'
    elif update_type == 'reviewer_change' and assigned_reviewers and unassigned_reviewers:
        update_type = 'assigned_and_unassigned_reviewers'

    switcher = {
        "target_change": "changed the target branch of",
        "new_commit": f"added a new commit <{deep_get(request.json,'object_attributes.last_commit.url')}|{deep_get(request.json,'object_attributes.last_commit.id')[:8]}> to",
        "unassigned_assignees": "unassigned " + ','.join(map(str, unassigned_assignees)) + " from",
        "unassigned_reviewers": "unassigned " + ','.join(map(str, unassigned_reviewers)) + " from reviewers of",
        "assigned_assignees": "assigned " + ','.join(map(str, assigned_assignees)) + " to",
        "assigned_reviewers": "asked " + ','.join(map(str, assigned_reviewers)) + " for a code review of",
        "assigned_and_unassigned_assignees": "assigned " + ','.join(
            map(str, assigned_assignees)) + ' and unassigned ' + ','.join(map(str, unassigned_assignees)) + " from",
        "assigned_and_unassigned_reviewers": "asked " + ','.join(
            map(str, assigned_reviewers)) + ' for a code review and unassigned ' + ','.join(
            map(str, unassigned_reviewers)) + " from reviewers of",
        "no_reviewers": "unassigned " + ','.join(map(str, unassigned_reviewers)) + " from reviewers of",
        "no_assignees": "unassigned " + ','.join(map(str, unassigned_assignees)) + " from"
    }

    result = switcher.get(update_type, 'None')
    return result


def parse_unassigned(old_users: str, new_users: str) -> []:
    """
    Return a list of users who were unassigned from the MR.

    :param old_users: str: string of old usernames
    :param new_users: str: string of new usernames
    :return: A list of users that were unassigned from the MR
    """
    initiator = deep_get(request.json, "user.username")
    users = [u for u in old_users.split(',') if u not in new_users.split(',') and u != 'None']
    for i, u in enumerate(users):
        if u.strip('@') == initiator:
            users[i] = 'themselves'

    return users


def parse_assigned(old_users: str, new_users: str) -> []:
    """
    Return a list of users who were assigned from the MR.

    :param old_users: str: string of old usernames
    :param new_users: str: string of new usernames
    :return: A list of users that were assigned to the MR
    """
    initiator = deep_get(request.json, "user.username")
    users = [u for u in new_users.split(',') if u not in old_users.split(',') and u != 'None']
    for i, u in enumerate(users):
        if u.strip('@') == initiator:
            users[i] = 'themselves'

    return users


def get_thread_start(data: Dict, history) -> Optional[Dict]:
    """
    Iterate through the Slack message history, looking for an event_type that matches 'mr_created' and an mr_id that
    matches the request's MR id.

    :param data: Dict: Webhook request data
    :param history: Dict: Dictionary of Slack messages
    :return: Matching message or None
    """
    for message in history:
        try:
            if (deep_get(message, "metadata.event_type") == 'mr_created' and deep_get(message, "metadata.event_payload.mr_id") ==
                    deep_get(data, "object_attributes.id")):
                return message
        except KeyError:
            pass
    return None


def parse_new_msg_status(assignees: str, reviewers: str) -> str:
    """
    Parse new MR into Slack message status

    :param reviewers: str: string of reviewers
    :param assignees: str: string of assignees
    :return: Status for a Slack message
    """
    status = STATUS_NEW

    if reviewers != 'None':
        status = STATUS_REVIEWING
    elif reviewers == 'None' and assignees != 'None':
        status = STATUS_ASSIGNED

    return status


# def parse_email_to_slack_id(email: str) -> Optional[str]:
#     """
#     Get Slack user ID by email. Will not be used for now because GitLab is redacting emails in their MR payload.
#     But, good to have for the future, when they solve this issue.
#     :param email: str
#     :return user_id | None
#     """
#     usr = slack_app.client.users_lookupByEmail(email=email)
#     return usr['user']['id'] if usr['ok'] else None

def parse_username_to_slack_id(username: str) -> Optional[str]:
    """
    Get Slack user ID by username. Retrieves the whole list of slack users and matches on either name or display_name.
    :param username: str
    :return user_id | None
    """
    username = config.SLACK_GITLAB_USER_MAPPING[username] if username in config.SLACK_GITLAB_USER_MAPPING.keys() \
        else username

    for usr in slack_user_list:
        if username in (usr.get('name', '').lower(), deep_get(usr, "profile.display_name").lower()):
            return usr.get('id', '')

    return None


def get_channel_id(channel_name: str) -> Optional[str]:
    """
    Get Slack channel id of a specific team
    :param channel_name: str: team name
    :return channel_id | ''
    """
    channel_id = config.TEAM_CHANNEL_MAPPING[channel_name] if channel_name in config.TEAM_CHANNEL_MAPPING.keys() \
        else ''

    return channel_id


def parse_request_to_nm_blocks(data: Dict, slack_id: str, mr_is_ready: bool) -> []:
    """"
    Generate Blocks for the new MR message
    :param mr_is_ready: Draft was marked as ready
    :param slack_id: str: Slack user id
    :param data: Dict: request data
    :return Slack message blocks for a new MR message
    """
    obj_attr = data.get('object_attributes', '')
    assignees = parse_users_to_string(False, 'assignees')
    reviewers = parse_users_to_string(False, 'reviewers')
    open_text = "has marked merge request as ready:" if mr_is_ready else "has created a new merge request:"
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"<@{slack_id}> {open_text} <{obj_attr.get('url', '')}|"
                        f"!{obj_attr.get('iid', '')}>: {obj_attr.get('title', '')}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"`{obj_attr.get('source_branch', '')}` → `{obj_attr.get('target_branch', '')}`"
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Project:*\n<{obj_attr.get('target', '').get('web_url', '')}"
                            f"|{obj_attr.get('target', '').get('name', '')}>"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Status:*\n{parse_new_msg_status(assignees, reviewers)}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Last Update:*\n{parse_date()}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Assignees:*\n{assignees}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Reviewers:*\n{reviewers}"
                }
            ]
        }
    ]


def parse_request_to_um_blocks(username: str, update_type: str, assignee_list: []) -> []:
    """"
    Generate Blocks for the update MR message
    :param assignee_list: []: List of old and new assignees
    :param update_type: str: Kind of update
    :param username: str: Slack username
    :return Slack message blocks for an update MR message
    """
    return [{

        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"{username.capitalize()} has {parse_action_into_message(update_type, assignee_list)} this merge request"
        }
    }]


def parse_request_to_nm_metadata(data: Dict) -> Dict:
    """"
    Generate metadata for the new MR message
    :param data: Dict: request data
    :return Slack message metadata dictionary
    """
    obj_attr = data.get('object_attributes', '')
    return {'event_type': "mr_created", 'event_payload': {'mr_id': obj_attr.get('id', ''),
                                                          'target_branch': obj_attr.get('target_branch', ''),
                                                          'assignees': parse_users_to_string(False,
                                                                                             'assignees'),
                                                          'reviewers': parse_users_to_string(False,
                                                                                             'reviewers')}}


def parse_request_to_um_metadata(data: Dict) -> Dict:
    """"
    Generate metadata for the update MR message
    :param data: Dict: request data
    :return Slack message metadata dictionary
    """
    return {'event_type': "mr_updated",
            'event_payload': {'mr_id': deep_get(data, "object_attributes.id")}}


def is_draft(title: str) -> bool:
    """
    Check if the MR is Draft
    :param title: str: Title of the MR
    :return: bool: Is MR draft
    """
    return any(substr in title for substr in DRAFT_SUBSTR)


def is_ready(action: str, changes: Optional[Dict]) -> bool:
    """
    Check if a Draft MR was marked as ready
    :param action: str: MR action
    :param changes: Optional[Dict]: canges in the MR
    :return: bool: Is MR marked as ready
    """
    try:
        return changes and action == 'update' and is_draft(deep_get(changes, "title.previous")) and not is_draft(
            deep_get(changes, "title.current"))
    except KeyError:
        return False
    except IndexError:
        return False


def set_user_list(user_list) -> None:
    """
    Set user list as a global variable
    :param user_list: list: List of usernames
    :return: None
    """
    global slack_user_list
    slack_user_list = user_list


def deep_get(dictionary: Dict, keys: str, default=''):
    """
    Find value by keys in a deep nested dictionary with lists
    :param dictionary: Dict: Dictionary
    :param keys: str: String of keys, e.g. "level1.level2.level3", can also pass list int index,
    like "level1.3.2.level4"
    :param default: str: Default value if key not found
    :return: str|list|Dict: value or ''
    """
    return reduce(lambda d, key: d.get(key, default) if isinstance(d, dict) else (d[int(key)] if isinstance(d, list)
                                                                   else default), keys.split("."), dictionary)