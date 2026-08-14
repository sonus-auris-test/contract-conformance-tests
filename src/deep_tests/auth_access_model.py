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


class ApplicationTab(Enum):
    HOME = "home"
    PLAYBACK = "playback"
    CONNECTIONS = "connections"
    AUTOMATION = "automation"
    CONFIGURE = "configure"


class DeletionSecondFactor(Enum):
    PHONE = "phone"
    AUTHENTICATOR = "totp"


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


def resolve_post_auth_tab(
    previous_tab: ApplicationTab, *, authentication_completed: bool
) -> ApplicationTab:
    """A fresh sign-in always enters the application through Home."""
    if not isinstance(previous_tab, ApplicationTab):
        raise ValueError("unknown application tab")
    return ApplicationTab.HOME if authentication_completed else previous_tab


def authorize_account_deletion(
    *,
    signed_in_email: str,
    confirmed_email: str,
    second_factor: DeletionSecondFactor | None,
    second_factor_verified_at: int | None,
    now: int,
    max_age_seconds: int = 300,
    future_clock_skew_seconds: int = 60,
) -> bool:
    """Reference policy for the irreversible account-deletion boundary."""
    if not signed_in_email.strip() or (
        signed_in_email.strip().casefold() != confirmed_email.strip().casefold()
    ):
        return False
    if second_factor not in (
        DeletionSecondFactor.PHONE,
        DeletionSecondFactor.AUTHENTICATOR,
    ):
        return False
    if second_factor_verified_at is None:
        return False
    if second_factor_verified_at > now + future_clock_skew_seconds:
        return False
    return now - second_factor_verified_at <= max_age_seconds
