from app import parser


class Thread:
    def __init__(self, history_thread, request):
        self.thread = history_thread
        self.target_branch = parser.deep_get(history_thread, "metadata.event_payload.target_branch")
        self.assignees = parser.deep_get(history_thread, "metadata.event_payload.assignees")
        self.assignee_text = parser.deep_get(history_thread, "blocks.3.fields.3.text")
        self.reviewers = parser.deep_get(history_thread, "metadata.event_payload.reviewers")
        self.reviewer_text = parser.deep_get(history_thread, "blocks.3.fields.4.text")
        self.target_branch_text = parser.deep_get(history_thread, "blocks.1.text.text")
        self.blocks = parser.deep_get(history_thread, "blocks")
        self.ts = parser.deep_get(history_thread, "ts")
        self.metadata = parser.deep_get(history_thread, "metadata")
        self.status = parser.deep_get(history_thread, "blocks.3.fields.1.text")
        self.old_assignees = parser.deep_get(history_thread, "metadata.event_payload.assignees")
        self.old_reviewers = parser.deep_get(history_thread, "metadata.event_payload.reviewers")
        self.text = ''
        self.update_type = ''

        self.set_updates(request)
        if self.update_type not in ["new_commit", "target_change"]:
            self.set_status(request)
        self.set_last_update()

    def set_target_branch(self, new_target):
        self.thread['metadata']['event_payload']['target_branch'] = new_target

    def set_assignees(self, new_assignees):
        self.assignees = new_assignees
        self.thread['metadata']['event_payload']['assignees'] = new_assignees

    def set_assignee_text(self, new_assignee_text):
        self.blocks[3]['fields'][3]['text'] = new_assignee_text

    def set_reviewers(self, new_reviewers):
        self.reviewers = new_reviewers
        self.thread['metadata']['event_payload']['reviewers'] = new_reviewers

    def set_reviewer_text(self, new_reviewer_text):
        self.blocks[3]['fields'][4]['text'] = new_reviewer_text

    def set_target_branch_text(self, new_target_branch_text):
        self.blocks[1]['text']['text'] = new_target_branch_text

    def set_last_update(self):
        self.blocks[3]['fields'][2]['text'] = f"*Last Update:*\n{parser.parse_date()}"

    def set_status(self, request):
        new_status = 'None'
        action = parser.deep_get(request, "object_attributes.action")

        if action != 'update':
            new_status = parser.parse_action_into_status(action)
        elif self.update_type in ['assignee_change', 'reviewer_change']:
            new_status = parser.parse_update_type_into_status(self.update_type, self.reviewers)
        elif self.update_type in ['no_reviewers', 'no_assignees']:
            new_status = parser.parse_no_users_into_status(self.status, self.reviewers, self.assignees,
                                                           self.update_type)

        if new_status != 'None':
            self.blocks[3]['fields'][1]['text'] = f"*Status:*\n{new_status}"

    def get_update_type(self):
        return self.update_type

    def set_update_type(self, update_type):
        self.update_type = update_type

    def get_target_branch(self):
        return self.target_branch

    def get_assignees(self):
        return self.assignees

    def get_reviewers(self):
        return self.reviewers

    def set_updates(self, request):
        new_assignees = self.assignees
        new_reviewers = self.reviewers

        if 'assignees' in request.get('changes', ''):
            new_assignees = parser.parse_users_to_string(True, 'assignees')
        elif 'reviewers' in request.get('changes', ''):
            new_reviewers = parser.parse_users_to_string(True, 'reviewers')

        target_branch = parser.deep_get(request, "object_attributes.target_branch")
        source_branch = parser.deep_get(request, "object_attributes.source_branch")

        if self.get_target_branch() != target_branch:
            self.set_target_branch(target_branch)
            self.set_target_branch_text(f"`{source_branch}` → `{target_branch}`")
            self.set_update_type('target_change')
        elif 'oldrev' in request.get('object_attributes', ''):
            self.set_update_type('new_commit')
        elif self.assignees != new_assignees:
            self.set_assignees(new_assignees)
            self.set_assignee_text(f"*Assignees:*\n{new_assignees}")

            if new_assignees != 'None':
                self.set_update_type('assignee_change')
            else:
                self.set_update_type('no_assignees')
        elif self.get_reviewers() != new_reviewers:
            self.set_reviewers(new_reviewers)
            self.set_reviewer_text(f"*Reviewers:*\n{new_reviewers}")
            if new_reviewers != 'None':
                self.set_update_type('reviewer_change')
            else:
                self.set_update_type('no_reviewers')
