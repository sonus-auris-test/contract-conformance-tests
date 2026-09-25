module web_session {
  type Phase = LoggedOut | OtpSent | SessionActive | Refreshing | Revoked

  type State = {
    phase: Phase,
    allowlisted: bool,
    otpVerified: bool,
    cookieIssued: bool,
    credentialsPersisted: bool,
    refreshValid: bool,
  }

  var s: State

  action init: bool = s' = {
    phase: LoggedOut,
    allowlisted: true,
    otpVerified: false,
    cookieIssued: false,
    credentialsPersisted: false,
    refreshValid: false,
  }

  action sendOtp: bool = all {
    s.phase == LoggedOut,
    s.allowlisted,
    s' = { ...s, phase: OtpSent },
  }

  action verifyOtp: bool = all {
    s.phase == OtpSent,
    s.allowlisted,
    s' = {
      ...s,
      phase: SessionActive,
      otpVerified: true,
      cookieIssued: true,
      credentialsPersisted: true,
      refreshValid: true,
    },
  }

  action beginRefresh: bool = all {
    s.phase == SessionActive,
    s.refreshValid,
    s' = { ...s, phase: Refreshing },
  }

  action refreshSuccess: bool = all {
    s.phase == Refreshing,
    s.allowlisted,
    s.refreshValid,
    s' = { ...s, phase: SessionActive },
  }

  action refreshFailure: bool = all {
    s.phase == Refreshing,
    s' = {
      ...s,
      phase: Revoked,
      cookieIssued: false,
      credentialsPersisted: false,
      refreshValid: false,
    },
  }

  action removeAllowlist: bool = all {
    Set(OtpSent, SessionActive, Refreshing).contains(s.phase),
    s' = {
      ...s,
      phase: Revoked,
      allowlisted: false,
      cookieIssued: false,
      credentialsPersisted: false,
      refreshValid: false,
    },
  }

  action signOut: bool = all {
    Set(SessionActive, Refreshing).contains(s.phase),
    s' = {
      ...s,
      phase: Revoked,
      cookieIssued: false,
      credentialsPersisted: false,
      refreshValid: false,
    },
  }

  action stutter: bool = s' = s

  action step: bool = any {
    sendOtp,
    verifyOtp,
    beginRefresh,
    refreshSuccess,
    refreshFailure,
    removeAllowlist,
    signOut,
    stutter,
  }

  val safety: bool = and {
    s.phase != SessionActive or and {
      s.allowlisted,
      s.otpVerified,
      s.cookieIssued,
      s.credentialsPersisted,
      s.refreshValid,
    },
    s.phase != Refreshing or and {
      s.allowlisted,
      s.otpVerified,
      s.cookieIssued,
      s.credentialsPersisted,
    },
    s.phase != Revoked or and {
      not(s.cookieIssued),
      not(s.credentialsPersisted),
      not(s.refreshValid),
    },
    not(s.cookieIssued) or s.credentialsPersisted,
  }

  val session_reachable: bool = s.phase == SessionActive
  val revoked_reachable: bool = s.phase == Revoked
}
