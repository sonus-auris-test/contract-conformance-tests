module infra_rollout {
  type Phase = Idle | Prepared | Canary | Promoted | RollingBack | RolledBack

  type State = {
    phase: Phase,
    credentialScopesValid: bool,
    canaryHealthy: bool,
    rollbackReady: bool,
    prodRouted: bool,
  }

  var s: State

  action init: bool = s' = {
    phase: Idle,
    credentialScopesValid: false,
    canaryHealthy: false,
    rollbackReady: false,
    prodRouted: false,
  }

  action prepare: bool = all {
    s.phase == Idle,
    s' = {
      ...s,
      phase: Prepared,
      credentialScopesValid: true,
      rollbackReady: true,
    },
  }

  action startCanary: bool = all {
    s.phase == Prepared,
    s.credentialScopesValid,
    s.rollbackReady,
    s' = { ...s, phase: Canary },
  }

  action markCanaryHealthy: bool = all {
    s.phase == Canary,
    s' = { ...s, canaryHealthy: true },
  }

  action promote: bool = all {
    s.phase == Canary,
    s.credentialScopesValid,
    s.canaryHealthy,
    s.rollbackReady,
    s' = { ...s, phase: Promoted, prodRouted: true },
  }

  action beginRollback: bool = all {
    s.phase == Promoted,
    s.rollbackReady,
    s' = { ...s, phase: RollingBack, prodRouted: false },
  }

  action finishRollback: bool = all {
    s.phase == RollingBack,
    s' = { ...s, phase: RolledBack, prodRouted: false },
  }

  action stutter: bool = s' = s

  action step: bool = any {
    prepare,
    startCanary,
    markCanaryHealthy,
    promote,
    beginRollback,
    finishRollback,
    stutter,
  }

  val safety: bool = and {
    not(s.prodRouted) or and {
      s.phase == Promoted,
      s.credentialScopesValid,
      s.canaryHealthy,
      s.rollbackReady,
    },
    not(Set(Prepared, Canary, Promoted, RollingBack, RolledBack).contains(s.phase))
      or s.credentialScopesValid,
    not(Set(RollingBack, RolledBack).contains(s.phase)) or not(s.prodRouted),
  }

  val promotion_reachable: bool = s.phase == Promoted and s.prodRouted
  val rollback_reachable: bool = s.phase == RolledBack and not(s.prodRouted)
}
