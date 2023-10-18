from util import get_gitlab, get_gitlab_requests, get_webhook_token
from requests import Response
from app import config


def edit_hook(project, hook_id, url, token) -> Response:
    if not config.ACCESS_GITLAB:
        return Response()
    data = {
        "url": url,
        "token": token,
        "merge_requests_events": True,
        "push_events": False
    }
    return get_gitlab_requests(type="PUT", path=f"/projects/{project.id}/hooks/{hook_id}", data=data)


def add_hook(project, url, token) -> Response:
    if not config.ACCESS_GITLAB:
        return Response()
    data = {
        "url": url,
        "token": token,
        "merge_requests_events": True,
        "push_events": False
    }
    return get_gitlab_requests(type="POST", path=f"/projects/{project.id}/hooks", data=data)


def get_hooks(project):
    return get_gitlab_requests(type="GET", path=f"/projects/{project.id}/hooks")


def main():
    gl = get_gitlab()
    squad = config.GITLAB_GROUP_ID_MAPPING["group_name"]  # enter your gitlab group name
    group = gl.groups.get(squad)
    projects = group.projects.list(archived=False)
    url = config.BOT_URL + squad.name.lower()
    token = get_webhook_token()
    for project in projects:
        res = get_hooks(project)
        hooks = res.json()
        project_has_hook = False
        for hook in hooks:
            if config.BOT_NAME in hook["url"]:
                project_has_hook = True
                res = edit_hook(project, hook["id"], url, token)
                print(res.status_code, project.id, project.name, "edited hook")
        if not project_has_hook:
            res = add_hook(project, url, token)
            print(res.status_code, project.id, project.name, "add hook")


if __name__ == "__main__":
    main()
