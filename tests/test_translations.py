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

import gettext
from pathlib import Path

import polib
from django.test import SimpleTestCase
from django.utils import translation

import jwt_allauth
from jwt_allauth.exceptions import IncorrectCredentials

LOCALE_DIR = Path(jwt_allauth.__file__).parent / 'locale'
LANGUAGES = sorted(p.name for p in LOCALE_DIR.iterdir() if p.is_dir())


def _source(code):
    return LOCALE_DIR / code / 'LC_MESSAGES' / 'django.po'


def _compiled(code):
    return LOCALE_DIR / code / 'LC_MESSAGES' / 'django.mo'


class CompiledCatalogueTests(SimpleTestCase):
    """``.po`` is for translators; ``.mo`` is the file gettext opens."""

    def test_every_language_ships_a_compiled_catalogue(self):
        # Nothing on the way to PyPI compiles these -- the release workflow runs
        # `python -m build` and no more -- so an uncompiled language is a language whose
        # translations never leave the repository.
        missing = [code for code in LANGUAGES if not _compiled(code).exists()]
        self.assertEqual(missing, [], 'run `django-admin compilemessages` and commit the result')

    def test_every_compiled_catalogue_carries_what_its_source_says(self):
        """
        The guard against a ``.po`` edited without recompiling, which is the failure that
        looks like a translation simply not taking.

        Compared by **content**, deliberately, and not by comparing modification times:
        git does not record them, so on a fresh clone every file carries the checkout
        time in whatever order the files landed, and a perfectly current ``.mo`` reads as
        older than its source about half the time. That check passed here and failed for
        all eleven languages on CI.
        """
        for code in LANGUAGES:
            with self.subTest(code):
                with open(_compiled(code), 'rb') as fh:
                    compiled = gettext.GNUTranslations(fh)
                for entry in polib.pofile(str(_source(code))):
                    self.assertEqual(
                        compiled.gettext(entry.msgid), entry.msgstr,
                        f'{code}: {entry.msgid!r} differs between the source and the compiled catalogue',
                    )

    def test_every_language_is_complete(self):
        # A half-translated catalogue answers part of a request in one language and the
        # rest in another, which is worse than answering all of it in English.
        for code in LANGUAGES:
            with self.subTest(code):
                po = polib.pofile(str(_source(code)))
                self.assertEqual([e.msgid for e in po.untranslated_entries()], [])
                self.assertEqual([e.msgid for e in po.fuzzy_entries()], [])

    def test_every_language_covers_the_same_strings(self):
        # Catches the language left out of a `makemessages` run: it keeps working and
        # silently stops covering whatever was added.
        reference = None
        for code in LANGUAGES:
            msgids = sorted(e.msgid for e in polib.pofile(str(_source(code))))
            if reference is None:
                reference, reference_code = msgids, code
            with self.subTest(code):
                self.assertEqual(msgids, reference, f'{code} and {reference_code} cover different strings')


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
