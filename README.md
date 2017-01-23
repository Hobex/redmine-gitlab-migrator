# Redmine to Gitlab migrator

[![Build Status](https://travis-ci.org/oasiswork/redmine-gitlab-migrator.svg?branch=master)](https://travis-ci.org/oasiswork/redmine-gitlab-migrator) [![PyPI version](https://badge.fury.io/py/redmine-gitlab-migrator.svg)](https://badge.fury.io/py/redmine-gitlab-migrator)

Migrate code projects from Redmine to Gitlab, keeping issues/milestones/metadata

_Note: although certainly not bugfree, this tool has been used at @oasiswork to migrate 30+ projects with 1000+ issues, and some attention is paid to keeping data._

## Does

- Per-project migrations
- Migration of issues, keeping as much metadata as possible:

  - redmine trackers become tags
  - issues comments are kept and assigned to the right users
  - issues final status (open/closed) are kept along with open/close date (not detailed status history)
  - issues assignments are kept
  - issues numbers (ex: `#123`)
  - issues/notes authors
  - issue/notes original dates, but as comments
  - relations (although gitlab model for relations is simpler)

- Migration of Versions/Roadmaps keeping:

  - issues composing the version
  - statuses & due dates

- Migration of wiki pages including history:

  - versions become older commits
  - author names (without email addresses!) are the author/committer names

## Does not

- Migrate users, groups, and permissions (redmine ACL model is complex and cannot be transposed 1-1 to gitlab ACL)
- Migrate repositories (piece of cake to do by hand, + redmine allows multiple repositories per project where gitlab does not)
- Migrate the whole redmine installation at once, because namespacing is different in redmine and gitlab
- Archive the redmine project for you
- Keep creation/edit dates as metadata
- Keep "watchers" on tickets (gitlab API v3 does not expose it)
- Keep dates/times as metadata
- Keep track of issue relations orientation (no such notion on gitlab)
- Remember who closed the issue
- Migrate tags ([redmine_tags](https://www.redmine.org/plugins/redmine_tags) plugin), as they are not exposed in gitlab API

## Requires

- Python >= 3.4
- gitlab >= 7.0
- redmine >= 1.3
- pandoc >= 1.17.0.0
- API token on redmine
- API token on gitlab (Private Account Token **not Access Token!**)
- No preexisting issues on gitlab project
- Already synced users (those required in the project you are migrating)

(It was developed/tested arround redmine 2.5.2, gitlab 8.2.0, python 3.4)

## Let's go

You can or can not use [virtualenvs](http://docs.python-guide.org/en/latest/dev/virtualenvs/), that's up to you.

Install it:

```
pip install redmine-gitlab-migrator
```

(or if you cloned the git: `python setup.py install`)

You can then give it a check without touching anything:

```
migrate-rg issues --redmine-key xxxx --gitlab-key xxxx \
  <redmine project url> <gitlab project url> --check
```

The `--check` here prevents any writing , it's available on all commands.

```
migrate-rg --help
```

## Migration process

This process is for each project, **order matters**.

### Create the gitlab project

It doesn't neet to be named the same, you just have to record it's URL (eg: _<https://git.example.com/mygroup/myproject>_).

### Create users

Manual operation, project members in gitlab need to have the same username as members in redmine. Every member that interacted with the redmine project should be added to the gitlab project. If a corresponding user can't be found in gitlab, the issue/comment will be assigned to the gitlab admin user.

### Migrate Roadmap

If you do use roadmaps, redmine _versions_ will be converted to gitlab _milestones_. If you don't, just skip this step.

```
migrate-rg roadmap --redmine-key xxxx --gitlab-key xxxx \
  https://redmine.example.com/projects/myproject \
  http://git.example.com/mygroup/myproject --check
```

_(remove `--check` to perform it for real, same applies for other commands)_

### Migrate issues

```
migrate-rg issues --redmine-key xxxx --gitlab-key xxxx \
  https://redmine.example.com/projects/myproject \
  http://git.example.com/mygroup/myproject --check
```

Note that your issue titles will be annotated with the original redmine issue ID, like _-RM-1186-MR-logging_. This annotation will be used (and removed) by the next step.

### Migrate Issues ID (iid)

You can retain the issues ID from redmine, **this cannot be done via REST API**, thus it requires **direct access to the gitlab machine**.

So you have to log in the gitlab machine (eg. via SSH), and then issue the commad with sufficient rights, from there:

```
migrate-rg iid --redmine --redmine-key xxxx --gitlab-key xxxx \
  https://redmine.example.com/projects/myproject \
  http://git.example.com/mygroup/myproject --check
```

### Migrate wiki pages

First, clone the GitLab wiki repository (go to your project's Wiki on GitLab, click on "Git Access" and copy the URL) somewhere local to your machine. The conversion process works even if there are pre-existing wiki pages, however this is NOT recommended.

```
migrate-rg pages --redmine-key xxxx --gitlab-wiki xxxx \
  https://redmine.example.com/projects/myproject \
```

where gitlab-wiki should be the path to the cloned repository (must be local to your machine). Add "--no-history" if you do not want the old versions of each page to be converted, too.

After conversion, verify that everything is correct (a copy of the original wiki page is included in the repo, however not added/commited), and then simply push it back to GitLab.

### Import git repository

A bare matter of `git remote set-url && git push`, see git documentation.

Note that gitlab does not support multiple repositories per project, you'll have to reorganize your projects if you were using that feature of Redmine.

### Archive redmine project

If you want to.

You're good to go :).

## Unit testing

Use the standard way:

```
python setup.py test
```

Or use whatever test runner you fancy.
