module supabase_target {
  type Phase = Planned | Baselined | Previewed | Connected | ProductionEnabled

  type State = {
    phase: Phase,
    baselineVerified: bool,
    rlsVerified: bool,
    branchProtectionVerified: bool,
    providerReadbackVerified: bool,
    destructiveReviewComplete: bool,
  }

  var s: State

  action init: bool = s' = {
    phase: Planned,
    baselineVerified: false,
    rlsVerified: false,
    branchProtectionVerified: false,
    providerReadbackVerified: false,
    destructiveReviewComplete: false,
  }

  action verifyBaseline: bool = all {
    s.phase == Planned,
    s' = { ...s, phase: Baselined, baselineVerified: true },
  }

  action verifyRls: bool = all {
    s.phase == Baselined,
    s.baselineVerified,
    s' = { ...s, rlsVerified: true },
  }

  action preview: bool = all {
    s.phase == Baselined,
    s.baselineVerified,
    s.rlsVerified,
    s' = { ...s, phase: Previewed },
  }

  action verifyBranchProtection: bool = all {
    s.phase == Previewed,
    s' = { ...s, branchProtectionVerified: true },
  }

  action verifyProviderReadback: bool = all {
    s.phase == Previewed,
    s' = { ...s, providerReadbackVerified: true },
  }

  action reviewDestructivePlan: bool = all {
    s.phase == Previewed,
    s' = { ...s, destructiveReviewComplete: true },
  }

  action connect: bool = all {
    s.phase == Previewed,
    s.baselineVerified,
    s.rlsVerified,
    s.branchProtectionVerified,
    s.providerReadbackVerified,
    s.destructiveReviewComplete,
    s' = { ...s, phase: Connected },
  }

  action enableProduction: bool = all {
    s.phase == Connected,
    s' = { ...s, phase: ProductionEnabled },
  }

  action disableProduction: bool = all {
    s.phase == ProductionEnabled,
    s' = { ...s, phase: Connected },
  }

  action stutter: bool = s' = s

  action step: bool = any {
    verifyBaseline,
    verifyRls,
    preview,
    verifyBranchProtection,
    verifyProviderReadback,
    reviewDestructivePlan,
    connect,
    enableProduction,
    disableProduction,
    stutter,
  }

  val gatesSatisfied: bool = and {
    s.baselineVerified,
    s.rlsVerified,
    s.branchProtectionVerified,
    s.providerReadbackVerified,
    s.destructiveReviewComplete,
  }

  val safety: bool = and {
    not(Set(Connected, ProductionEnabled).contains(s.phase)) or gatesSatisfied,
    s.phase != Previewed or and { s.baselineVerified, s.rlsVerified },
    not(s.providerReadbackVerified) or s.baselineVerified,
  }

  val production_reachable: bool = s.phase == ProductionEnabled
  val disabled_after_production_reachable: bool = s.phase == Connected and gatesSatisfied
}
