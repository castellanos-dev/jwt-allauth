.. meta::
   :description: Rotating refresh tokens does not detect theft on its own. How replay
       detection works, why a blacklist is not enough, and what it takes to implement
       session revocation correctly in Django REST Framework.

Refresh token rotation is not enough
====================================

Rotation is the standard advice for refresh tokens, and every Django JWT stack
implements it: each time a refresh token is exchanged for an access token, it is
replaced by a new one and the old one stops working.

It is good advice. It is also, on its own, close to useless against the attack it is
usually recommended for.

This page explains why, what has to be added, and where the subtleties are. It is
written against Django REST Framework and Simple JWT, but nothing in the reasoning is
specific to them.


The scenario
------------

A refresh token leaks. Choose your favourite mechanism: an XSS payload reading
``localStorage``, a stolen backup, a proxy log, a compromised device that was never
wiped. What matters is the end state — the attacker holds a valid refresh token, and so
does the legitimate user, and they are the same token.

Now both of them call the refresh endpoint.

Whoever calls first gets a new access token and a new refresh token, and their session
carries on. Whoever calls second presents a token that has already been rotated.

Everything hinges on what the server does with that second request.


What rotation alone does
------------------------

Without any server-side record, nothing. A refresh token is a signed JWT; if it verifies
and has not expired, it is valid. "Already rotated" is not a property of the token — it
is a property of a history the server did not keep. Both parties refresh happily, for as
long as the tokens keep being renewed, which is forever.

Rotation without server-side state is a naming convention.


What a blacklist does
---------------------

This is what Simple JWT's ``token_blacklist`` app gives you, with
``ROTATE_REFRESH_TOKENS`` and ``BLACKLIST_AFTER_ROTATION`` both on: a rotated token is
written to a deny-list, and a token found on that list is rejected.

That closes the previous hole — the second caller is refused. But look at who the second
caller is.

If the attacker refreshes first, the attacker gets a working session. The legitimate
user refreshes second, is rejected, and is logged out. The user re-authenticates,
assumes a glitch, and carries on. **The attacker keeps a valid, indefinitely renewable
session, and the theft never surfaces.**

The blacklist treats a replay as an invalid request. It is not an invalid request. It is
the one observable signal that a credential has been copied, and it deserves a response
proportional to that.


Reuse detection
---------------

The response is to revoke the whole session — every token descended from the same login,
including the one the attacker just obtained. Both parties are logged out, and both have
to authenticate again. The attacker has a password prompt in front of them; the user has
their password.

This is not a novel idea. It is `OAuth 2.0 Security Best Current Practice §4.14.2
<https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics#section-4.14.2>`_:

    If a refresh token is compromised and subsequently used by both the attacker and the
    legitimate client, one of them will present an invalidated refresh token, which will
    inform the authorization server of the breach. The authorization server cannot
    determine which party submitted the invalid refresh token, but it will revoke the
    active refresh token.

The phrasing that matters is *cannot determine which party*. You are not identifying the
attacker. You are ending a session that is known to be shared, and the cost of being
wrong is one re-login.


Turning the deny-list into an allow-list
----------------------------------------

To revoke a session you have to be able to name it, which a deny-list cannot do: it
records tokens that are dead, and says nothing about which live tokens belong together.

So the record has to be inverted. Instead of writing down rotated tokens, write down
live ones:

- Every login creates a **session**, identified by a value carried in a claim and copied
  unchanged into every token rotated from it.
- Every live refresh token has a row: its ``jti``, and the session it belongs to.
- Rotation deletes the presented token's row and inserts the successor's.
- A token whose ``jti`` has no row is a replay. Delete every row for its session.

The list stays small — one row per live session, not one per token ever issued — and it
answers questions a deny-list cannot: which sessions does this user have open, on what
devices, and end that one.

It also removes the need for a separate cleanup story for the deny-list, which otherwise
grows without bound for the lifetime of the deployment.


Four things that are easy to get wrong
--------------------------------------

The idea is simple. The implementation has sharp edges, and the failure modes are silent.

**1. Claiming the token has to be atomic.**

Two requests presenting the same token at the same moment must not both succeed. If both
read the row, both find it, and both insert a successor, one credential has become two
live sessions — and the replay that would have revealed the theft has been swallowed.

Read the row ``FOR UPDATE``, and treat the deletion as the claim rather than a cleanup
step: only the request whose ``DELETE`` reports a row is allowed to mint the successor.
The deleted-row count is a portable tiebreaker on backends without row locking.

.. code-block:: python

    with transaction.atomic():
        rows = list(RefreshTokenWhitelist.objects.select_for_update().filter(jti=jti))
        if not rows:
            raise Replayed          # not whitelisted: rotated already, or forged
        deleted, _ = RefreshTokenWhitelist.objects.filter(pk=rows[0].pk).delete()
        if deleted == 0:
            raise Replayed          # lost the race to another rotation
        # ...only now is it safe to issue the successor

**2. The revocation must outlive the transaction that detected it.**

A replay is detected inside the rotation, and the rotation fails. If the revocation runs
in that same transaction it is rolled back with it, and the session it was supposed to
destroy survives — the detection works perfectly and changes nothing.

Let the rejection escape the atomic block, and revoke after it has unwound.

**3. Revocation and rotation race each other.**

Rotation deletes one row and inserts another. A revocation running concurrently can read
the set of rows before the insert and delete them after it — leaving the successor
behind. The session survives the logout that reported it closed, which is the same class
of bug as the one being fixed, arrived at from the other side.

Both operations need to take a lock on the *user*, not on the row, since the row they
disagree about is the one that does not exist yet.

**4. Reuse detection only fires if the user comes back.**

If the attacker steals a token from a device the user has abandoned, no replay ever
happens, and there is nothing to detect. Reuse detection is triggered by contention; a
credential nobody contests stays valid for as long as it keeps being rotated.

The backstop is an absolute session lifetime: a claim recording when the session
*started*, copied across rotations, past which no rotation is honoured however recently
the last one happened. Without it, "sessions stay alive while in use" means an attacker
who keeps refreshing stays in indefinitely.


What this still does not solve
------------------------------

Access tokens are self-contained. Revoking a session stops rotation, but access tokens
already issued for it remain valid until they expire, because verifying them touches no
database — which is the entire point of using them. Short access token lifetimes bound
that window; checking each request against the session list closes it, at the cost of one
query per request and of the statelessness you chose JWTs for.

There is no version of this where a stolen token is worthless the instant it is stolen.
The goal is to bound the damage and to make the theft observable.


In JWT Allauth
--------------

All of the above is what this library implements, which is why
``BLACKLIST_AFTER_ROTATION = True`` raises at startup rather than being merely
discouraged: the deny-list and the allow-list are answers to the same question, and
running both means one of them is wrong.

- The whitelist and the ``session`` claim: :doc:`refresh_token`
- Absolute session lifetime, ``JWT_ALLAUTH_SESSION_LIFETIME``: :doc:`refresh_token`
- Per-request revocation checks, ``JWT_ALLAUTH_ACCESS_TOKEN_SESSION_CHECK``:
  :doc:`refresh_token`

If you are building this yourself instead, the four failure modes above are the ones
worth writing tests for. They are all invisible in the happy path.
