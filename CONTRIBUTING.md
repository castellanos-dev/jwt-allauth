Contributing
============

Thanks for looking. This is a small project with one maintainer, so the most useful
thing you can send is something that is easy to say yes to.

**Found a security problem?** Do not open an issue — see [SECURITY.md](SECURITY.md).


Getting set up
--------------

```bash
git clone https://github.com/castellanos-dev/jwt-allauth.git
cd jwt-allauth
python -m venv .venv && source .venv/bin/activate
pip install -r dev-requirements.txt
python runtests.py
```

`runtests.py` runs the whole suite against `tests/settings.py`. It disables migrations
for `jwt_allauth`, so there is no database to prepare.


Before you open a pull request
------------------------------

```bash
tox -e lint          # flake8, 120 columns
tox -e py310-min     # the dependency floor
tox -e py313-latest  # whatever resolves today
```

`tox -e py312-lts` covers the Django LTS in between. `py313-latest` deliberately has no
upper bounds on its dependencies, so it is the environment that catches a breaking
upstream release — if it fails and your branch did not touch that area, say so in the
pull request rather than working around it.


What a good pull request looks like
-----------------------------------

**Tests.** Every behavioural change needs one. For anything touching sessions, tokens or
permissions, the test that matters is the one that fails before the change: a test that
only demonstrates the new happy path does not show that the old behaviour was wrong.

**One thing at a time.** A bug fix and a refactor of the surrounding code are two pull
requests. The second is much easier to review once the first is merged.

**Comments that say why.** The convention in this codebase is that comments explain the
reasoning that is not visible in the code — the race being guarded against, the ordering
that matters, the case that made a defensive branch necessary. Comments restating what
the line does get removed in review.

**Say what you did not do.** A partial fix with its limits written down is more useful
than one that looks complete and is not.


Things worth knowing before you change them
-------------------------------------------

- **Session bookkeeping is concurrent.** Rotation, revocation and logout all write the
  same set of rows and race each other. `user_sessions_lock` orders them, and the
  ordering is load-bearing — see `jwt_allauth/token_refresh/serializers.py` and
  [Refresh token rotation is not enough](https://jwt-allauth.readthedocs.io/en/latest/refresh_token_theft.html).
  If you are changing this, `tests/test_session_concurrency.py` and
  `tests/test_session_revocation.py` are where to start.

- **The upstream coupling is not all public API.** Simple JWT's token and authentication
  classes are subclassed and its settings rewritten in `AppConfig.ready`; allauth's TOTP
  and recovery-code helpers come from under `internal`. Adding a new import from an
  upstream `internal` module needs a reason, because it is what the startup version check
  (`jwt_allauth.checks.check_upstream_versions`) exists to warn about.

- **No upper bounds on dependencies.** If a new upstream release breaks something, the
  fix is to support it, not to cap it. The reasoning is in `pyproject.toml`.

- **Migrations are not shipped.** `jwt_allauth/migrations/` holds only `__init__.py`;
  projects generate their own. A model change is therefore a breaking change for every
  installation, so it needs to be worth it.


Documentation
-------------

Docs live in `docs/source` and build with `python -m sphinx -b html source _build`. If
your change adds or alters a setting, it belongs in the relevant page **and** in
`release_notes.rst` — the release notes are written for someone deciding whether to
upgrade, so say what changes for them, not what you edited.


Reporting a bug
---------------

Include the versions (`django-jwt-allauth`, Django, `django-allauth`, Simple JWT), the
relevant settings, and the shortest sequence of requests that reproduces it. A failing
test against `tests/settings.py` is the fastest possible route to a fix.
