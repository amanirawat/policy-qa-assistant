---
title: NIST SP 800-63B - Authentication and Authenticator Management (Password Guidance)
publisher: NIST
url: https://csrc.nist.gov/pubs/sp/800/63/b/4/final
note: Starter summary written for this project in plain language. Verify against the official publication before relying on it.
---

# Password Guidance (NIST SP 800-63B)

## Minimum and maximum password length
When a password is the only factor used to sign in, NIST recommends requiring at least 15 characters. When a password is used together with another factor as part of multi-factor authentication, the minimum is 8 characters. Systems should allow passwords of at least 64 characters so people can use long passphrases. Spaces and all printable characters, including Unicode, should be accepted.

## Password complexity and composition rules
Organizations should not require composition rules such as "must include an uppercase letter, a number, and a symbol." Research shows these rules push people toward predictable patterns like Password1! and do not meaningfully improve security. Length is a better lever than forced complexity.

## Password expiration and periodic changes
Do not force users to change passwords on a fixed schedule, such as every 90 days. A password change should be required only when there is evidence that the password has been compromised, for example after a breach or a phishing incident.

## Blocklists of common and compromised passwords
When a user creates or changes a password, the system should compare it against a blocklist of values that are commonly used, expected, or known to be compromised. This includes passwords found in breach data, dictionary words, repetitive or sequential characters such as aaaaaa or 1234abcd, and context-specific words such as the name of the service or the username. If the new password matches the blocklist, it should be rejected and the user should be told why.

## Password managers, paste, and showing the password
Systems should allow users to paste passwords so that password managers work. Users should be offered an option to display the password while typing it, which reduces typing errors with long passphrases.

## Password hints and security questions
Password hints that are visible to unauthenticated users should not be offered. Knowledge-based security questions, such as the name of a first pet, should not be used to authenticate users because the answers are often easy to guess or find online.

## Failed login attempts and rate limiting
Systems should limit the number of consecutive failed sign-in attempts on an account, to no more than 100. Additional techniques such as increasing delays between attempts or requiring a CAPTCHA can slow down guessing attacks.

## How passwords should be stored
Passwords must never be stored in plain text. They should be salted and hashed using an approved password hashing or key derivation function that is designed to resist offline guessing attacks.

## Multi-factor authentication and phishing resistance
Higher assurance levels require multi-factor authentication. Phishing-resistant authenticators, such as FIDO2 or WebAuthn security keys and PIV smart cards, provide the strongest protection. One-time codes sent by SMS or voice call are treated as restricted authenticators because they can be intercepted or redirected through SIM swapping.
