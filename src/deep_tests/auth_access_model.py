from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AssuranceLevel(Enum):
    SIGNED_OUT = "signed_out"
    AAL1 = "aal1"
    AAL2 = "aal2"


class AccessDestination(Enum):
    EMAIL_OTP = "email_otp"
    MFA = "mfa"
    ACCOUNT_RECOVERY = "account_recovery"
    ONBOARDING = "onboarding"
    VOICE_UNLOCK = "voice_unlock"
    APPLICATION = "application"


@dataclass(frozen=True)
class AccessState:
    assurance: AssuranceLevel
    account_recovery_pending: bool = False
    onboarding_complete: bool = False
    voice_unlock_enabled: bool = False
    voice_unlock_locked: bool = False


def resolve_access(state: AccessState) -> AccessDestination:
    """Resolve Sonus Auris access in strict fail-closed priority order."""
    if not isinstance(state.assurance, AssuranceLevel):
        raise ValueError("unknown authentication assurance level")
    if state.assurance is AssuranceLevel.SIGNED_OUT:
        return AccessDestination.EMAIL_OTP
    if state.assurance is AssuranceLevel.AAL1:
        return AccessDestination.MFA
    if state.account_recovery_pending:
        return AccessDestination.ACCOUNT_RECOVERY
    if not state.onboarding_complete:
        return AccessDestination.ONBOARDING
    if state.voice_unlock_enabled and state.voice_unlock_locked:
        return AccessDestination.VOICE_UNLOCK
    return AccessDestination.APPLICATION
