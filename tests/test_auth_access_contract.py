from __future__ import annotations

import itertools
import unittest
from dataclasses import replace

from deep_tests.auth_access_model import (
    AccessDestination,
    AccessState,
    AssuranceLevel,
    resolve_access,
)


BOOLEAN_FLAG_COMBINATIONS = tuple(itertools.product((False, True), repeat=4))


def state_for(
    assurance: AssuranceLevel,
    flags: tuple[bool, bool, bool, bool],
) -> AccessState:
    recovery, onboarding, voice_enabled, voice_locked = flags
    return AccessState(
        assurance=assurance,
        account_recovery_pending=recovery,
        onboarding_complete=onboarding,
        voice_unlock_enabled=voice_enabled,
        voice_unlock_locked=voice_locked,
    )


class AuthenticationAccessContractTests(unittest.TestCase):
    def test_signed_out_always_resolves_to_email_otp(self) -> None:
        for flags in BOOLEAN_FLAG_COMBINATIONS:
            with self.subTest(flags=flags):
                destination = resolve_access(
                    state_for(AssuranceLevel.SIGNED_OUT, flags)
                )
                self.assertIs(destination, AccessDestination.EMAIL_OTP)

    def test_aal1_always_resolves_to_mandatory_mfa(self) -> None:
        for flags in BOOLEAN_FLAG_COMBINATIONS:
            with self.subTest(flags=flags):
                destination = resolve_access(state_for(AssuranceLevel.AAL1, flags))
                self.assertIs(destination, AccessDestination.MFA)

    def test_aal2_preserves_recovery_onboarding_and_voice_unlock_order(self) -> None:
        cases = (
            (
                AccessState(
                    assurance=AssuranceLevel.AAL2,
                    account_recovery_pending=True,
                    onboarding_complete=False,
                    voice_unlock_enabled=True,
                    voice_unlock_locked=True,
                ),
                AccessDestination.ACCOUNT_RECOVERY,
            ),
            (
                AccessState(
                    assurance=AssuranceLevel.AAL2,
                    onboarding_complete=False,
                    voice_unlock_enabled=True,
                    voice_unlock_locked=True,
                ),
                AccessDestination.ONBOARDING,
            ),
            (
                AccessState(
                    assurance=AssuranceLevel.AAL2,
                    onboarding_complete=True,
                    voice_unlock_enabled=True,
                    voice_unlock_locked=True,
                ),
                AccessDestination.VOICE_UNLOCK,
            ),
            (
                AccessState(
                    assurance=AssuranceLevel.AAL2,
                    onboarding_complete=True,
                    voice_unlock_enabled=True,
                    voice_unlock_locked=False,
                ),
                AccessDestination.APPLICATION,
            ),
        )
        for state, expected in cases:
            with self.subTest(state=state):
                self.assertIs(resolve_access(state), expected)

    def test_sign_out_and_assurance_downgrade_immediately_relock_every_route(
        self,
    ) -> None:
        for flags in BOOLEAN_FLAG_COMBINATIONS:
            authenticated = state_for(AssuranceLevel.AAL2, flags)
            with self.subTest(flags=flags, transition="sign_out"):
                self.assertIs(
                    resolve_access(
                        replace(authenticated, assurance=AssuranceLevel.SIGNED_OUT)
                    ),
                    AccessDestination.EMAIL_OTP,
                )
            with self.subTest(flags=flags, transition="aal2_to_aal1"):
                self.assertIs(
                    resolve_access(
                        replace(authenticated, assurance=AssuranceLevel.AAL1)
                    ),
                    AccessDestination.MFA,
                )

    def test_unknown_assurance_level_fails_closed(self) -> None:
        state = AccessState(assurance=AssuranceLevel.AAL2, onboarding_complete=True)
        object.__setattr__(state, "assurance", "unexpected")
        with self.assertRaisesRegex(
            ValueError, "unknown authentication assurance level"
        ):
            resolve_access(state)


if __name__ == "__main__":
    unittest.main()
