"""
The translation catalogues, and whether they reach a running installation at all.

Two things can be wrong with a catalogue and neither shows up anywhere else. It can be
*stale* -- the one shipped until 1.5.1 was inherited from this project's ancestor and
still translated strings like "View is not defined, pass it as a context variable",
which no longer exist, while every string the library actually raises went out in
English. And it can be *inert*: Django reads the compiled ``.mo`` and never the ``.po``,
so a catalogue that is not compiled and shipped translates nothing no matter how
complete it is.

So these tests check the two facts that matter to somebody who installs the package: the
catalogues cover the strings the code really uses, and a translation actually comes back
out of ``gettext`` under a language the package claims to support.
"""

import os
from pathlib import Path

from django.test import SimpleTestCase
from django.utils import translation

import jwt_allauth
from jwt_allauth.exceptions import IncorrectCredentials

LOCALE_DIR = Path(jwt_allauth.__file__).parent / 'locale'
LANGUAGES = sorted(p.name for p in LOCALE_DIR.iterdir() if p.is_dir())


class CompiledCatalogueTests(SimpleTestCase):
    """``.po`` is for translators; ``.mo`` is the file gettext opens."""

    def test_every_language_ships_a_compiled_catalogue(self):
        # Nothing on the way to PyPI compiles these -- the release workflow runs
        # `python -m build` and no more -- so an uncompiled language is a language whose
        # translations never leave the repository.
        missing = [
            code for code in LANGUAGES
            if not (LOCALE_DIR / code / 'LC_MESSAGES' / 'django.mo').exists()
        ]
        self.assertEqual(missing, [], 'run `django-admin compilemessages` and commit the result')

    def test_no_compiled_catalogue_is_older_than_its_source(self):
        # A `.mo` left behind by an edit to the `.po` is the failure mode that looks like
        # a translation that simply did not take.
        stale = []
        for code in LANGUAGES:
            source = LOCALE_DIR / code / 'LC_MESSAGES' / 'django.po'
            compiled = LOCALE_DIR / code / 'LC_MESSAGES' / 'django.mo'
            if compiled.exists() and os.path.getmtime(compiled) < os.path.getmtime(source):
                stale.append(code)
        self.assertEqual(stale, [], 'recompile these catalogues')


class TranslationsAreActuallyAppliedTests(SimpleTestCase):
    """
    The end-to-end fact: a string this library raises comes back translated.

    Deliberately goes through ``gettext`` rather than reading the ``.po``, because
    everything between the catalogue and the caller -- the app being on the locale path,
    the ``Language`` header being set, the file being compiled -- is exactly what used to
    be broken and what a file-level assertion would not have noticed.
    """

    # One per language: a short string with no room for a defensible variant, so the
    # test pins delivery rather than anybody's wording.
    LOGGED_OUT = {
        'es': 'Sesión cerrada correctamente.',
        'fr': 'Déconnexion réussie.',
        'de': 'Erfolgreich abgemeldet.',
        'pt_BR': 'Sessão encerrada com sucesso.',
        'ru': 'Выход выполнен успешно.',
        'pl': 'Wylogowano pomyślnie.',
        'cs': 'Odhlášení proběhlo úspěšně.',
        'tr': 'Başarıyla çıkış yapıldı.',
        'ko': '성공적으로 로그아웃되었습니다.',
        'zh_Hans': '已成功退出登录。',
        'zh_Hant': '已成功登出。',
    }

    def test_every_shipped_language_is_covered_by_this_test(self):
        self.assertEqual(sorted(self.LOGGED_OUT), LANGUAGES)

    def test_each_language_translates_a_string_the_library_raises(self):
        for code, expected in self.LOGGED_OUT.items():
            with self.subTest(code), translation.override(code):
                self.assertEqual(translation.gettext('Successfully logged out.'), expected)

    def test_an_exception_detail_is_translated_when_it_is_rendered(self):
        # `default_detail` is a lazy string, so it resolves in the active language of the
        # request rather than in the one in force when the exception class was imported.
        # `detail` is the dict simplejwt's `DetailDictMixin` builds, carrying the
        # localized message beside the code a client branches on.
        with translation.override('fr'):
            self.assertEqual(str(IncorrectCredentials().detail['detail']), 'Identifiants incorrects')

    def test_english_is_left_alone(self):
        with translation.override('en'):
            self.assertEqual(translation.gettext('Successfully logged out.'), 'Successfully logged out.')
