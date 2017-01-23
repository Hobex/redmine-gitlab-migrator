""" Convert Redmine objects to gitlab's
"""

import logging


log = logging.getLogger(__name__)

# Utils

def status_text(issue_statuses, status):
    return issue_statuses.get(str(status), {'name': 'Unknown'})['name']

def is_closed_issue(issue_statuses, status):
    return issue_statuses.get(str(status), {}).get('is_closed', False)

def redmine_uid_to_login(redmine_id, redmine_user_index):
    login = redmine_user_index[redmine_id]['login']
    if "@" in login:
        login = login.rsplit('@', 1)[0]
    return login


def redmine_uid_to_gitlab_uid(redmine_id,
                              redmine_user_index, gitlab_user_index):
    username = redmine_uid_to_login(redmine_id, redmine_user_index)
    return gitlab_user_index[username]['id']


def convert_notes(redmine_issue_journals, redmine_user_index, issue_statuses, textile_converter):
    """ Convert a list of redmine journal entries to gitlab notes

    Filters out the empty notes (ex: bare status change)
    Adds metadata as comment

    :param redmine_issue_journals: list of redmine "journals"
    :return: yielded couple ``data``, ``meta``. ``data`` is the API payload for
        an issue note and meta a dict (containing, at the moment, only a
        "sudo_user" key).
    """

    closed = False
    for entry in redmine_issue_journals:
        journal_notes = entry.get('notes', '')
        created_at = entry.get('created_on', '')
        try:
            author = redmine_uid_to_login(
                entry['user']['id'], redmine_user_index)
        except KeyError:
            # In some cases you have anonymous notes, which do not exist in
            # gitlab.
            log.warning(
                'Redmine user {} is unknown, attribute note '
                'to current admin\n'.format(entry['user']))
            author = None

        if len(journal_notes) > 0:
            try:
                yield {'body': textile_converter.convert(journal_notes), 'created_at': created_at}, {'sudo_user': author}
            except:
                yield {'body': 'Conversion error. Please see original issue.', 'created_at': created_at}, {'sudo_user': author}
        for property in entry['details']:
            if property.get('name', '') == 'status_id':
                current_closed = is_closed_issue(issue_statuses, property.get('new_value'))
                if closed != current_closed:
                    closed = current_closed
                    yield {'updated_at': created_at, 'state_event': 'close' if closed else 'reopen'}, {'sudo_user': author, 'must_close': True}


def relations_to_string(relations, issue_id):
    """ Convert redmine formal relations to some denormalized string

    That's the way gitlab does relations, by "mentioning".

    :param relations: list of issues relations
    :param issue_id: the current issue id
    :return a string listing relations.
    """
    l = []
    for i in relations:
        if issue_id == i['issue_id']:
            other_issue_id = i['issue_to_id']
        else:
            other_issue_id = i['issue_id']
        l.append('{} #{}'.format(i['relation_type'], other_issue_id))

    return ', '.join(l)


# Convertor

def convert_issue(redmine_issue, redmine_user_index, gitlab_user_index,
                  gitlab_milestones_index, issue_statuses, textile_converter, redmine_url):
    relations = redmine_issue.get('relations', [])
    relations_text = relations_to_string(relations, redmine_issue['id'])
    if len(relations_text) > 0:
        relations_text = ', ' + relations_text

    labels = redmine_issue['tracker']['name'] + ',' + redmine_issue['status']['name']

    # category is optional
    try:
        labels += ',' + redmine_issue['category']['name']
    except:
        pass

    data = {
        'iid': redmine_issue['id'],
        'title': redmine_issue['subject'],
        'description': '{}\n\n{}\n\n{}/issues/{}'.format(
            textile_converter.convert(redmine_issue['description']),
            relations_text,
            redmine_url,
            redmine_issue['id']
        ),
        'created_at': redmine_issue['created_on'],
        'labels': labels
    }

    version = redmine_issue.get('fixed_version', None)
    if version:
        data['milestone_id'] = gitlab_milestones_index[version['name']]['id']

    try:
        author_login = redmine_uid_to_login(
            redmine_issue['author']['id'], redmine_user_index)

    except KeyError:
        log.warning(
            'Redmine issue #{} is anonymous, gitlab issue is attributed '
            'to current admin\n'.format(redmine_issue['id']))
        author_login = None

    meta = {
        'sudo_user': author_login,
        'notes': list(convert_notes(redmine_issue['journals'],
                                    redmine_user_index, issue_statuses, textile_converter))
    }

    if redmine_issue.get('closed_on', None):
        # quick'n dirty extract date
        meta['closed_at'] = redmine_issue.get('closed_on')
        meta['must_close'] = True
    else:
        meta['must_close'] = False

    assigned_to = redmine_issue.get('assigned_to', None)
    if assigned_to is not None:
        data['assignee_id'] = redmine_uid_to_gitlab_uid(
            assigned_to['id'], redmine_user_index, gitlab_user_index)
    return data, meta


def convert_version(redmine_version):
    """ Turns a redmine version into a gitlab milestone

    Do not handle the issues linked to the milestone/version.
    Note that redmine do not expose a due date in API.

    :param redmine_version: a dict describing redmine-api-style version
    :rtype: couple: dict, dict
    :return: a dict describing gitlab-api-style milestone and another for meta
    """
    milestone = {
        "title": redmine_version['name'],
        "description": '{}\n\n*(from redmine: created on {})*'.format(
            redmine_version['description'],
            redmine_version['created_on'][:10])
    }
    if 'due_date' in redmine_version:
        milestone['due_date'] = redmine_version['due_date'][:10]

    must_close = redmine_version['status'] == 'closed'

    return milestone, {'must_close': must_close}
