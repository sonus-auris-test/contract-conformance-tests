module lambda_delivery {
  type Phase = Idle | Running | Retrying | Succeeded | DeadLetter

  type State = {
    phase: Phase,
    attempts: int,
    idempotencyRecorded: bool,
    effectCount: int,
  }

  var s: State
  pure val MAX_ATTEMPTS: int = 3

  action init: bool = s' = {
    phase: Idle,
    attempts: 0,
    idempotencyRecorded: false,
    effectCount: 0,
  }

  action start: bool = all {
    s.phase == Idle,
    s' = { ...s, phase: Running, attempts: 1 },
  }

  action recordIdempotency: bool = all {
    s.phase == Running,
    not(s.idempotencyRecorded),
    s' = { ...s, idempotencyRecorded: true },
  }

  action commitEffect: bool = all {
    s.phase == Running,
    s.idempotencyRecorded,
    s.effectCount == 0,
    s' = { ...s, effectCount: 1 },
  }

  action retry: bool = all {
    s.phase == Running,
    s.attempts < MAX_ATTEMPTS,
    s' = { ...s, phase: Retrying },
  }

  action resumeRetry: bool = all {
    s.phase == Retrying,
    s.attempts < MAX_ATTEMPTS,
    s' = { ...s, phase: Running, attempts: s.attempts + 1 },
  }

  action succeed: bool = all {
    s.phase == Running,
    s.effectCount == 1,
    s' = { ...s, phase: Succeeded },
  }

  action deadLetter: bool = all {
    s.phase == Running,
    s.attempts == MAX_ATTEMPTS,
    s.effectCount == 0,
    s' = { ...s, phase: DeadLetter },
  }

  action stutter: bool = s' = s

  action step: bool = any {
    start,
    recordIdempotency,
    commitEffect,
    retry,
    resumeRetry,
    succeed,
    deadLetter,
    stutter,
  }

  val safety: bool = and {
    s.attempts >= 0,
    s.attempts <= MAX_ATTEMPTS,
    s.effectCount >= 0,
    s.effectCount <= 1,
    s.effectCount == 0 or s.idempotencyRecorded,
    s.phase != Succeeded or s.effectCount == 1,
    s.phase != DeadLetter or s.effectCount == 0,
  }

  val success_reachable: bool = s.phase == Succeeded
  val dead_letter_reachable: bool = s.phase == DeadLetter
}
