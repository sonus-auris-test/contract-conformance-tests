module client_transport {
  type Phase = Idle | Requesting | Succeeded | Rejected
  type RequestKind = Probe | StorageGet | StoragePut

  type State = {
    phase: Phase,
    kind: RequestKind,
    baseValid: bool,
    redirectFollowed: bool,
    apiCredentialAttached: bool,
    signedStorageCredentialAttached: bool,
    bodyBytes: int,
    objectJson: bool,
    transferWithinBound: bool,
  }

  var s: State
  pure val PROBE_SUCCESS_MAX_BYTES: int = 65536

  action init: bool = s' = {
    phase: Idle,
    kind: Probe,
    baseValid: false,
    redirectFollowed: false,
    apiCredentialAttached: false,
    signedStorageCredentialAttached: false,
    bodyBytes: 0,
    objectJson: false,
    transferWithinBound: false,
  }

  action rejectInvalidBase: bool = all {
    s.phase == Idle,
    s' = { ...s, phase: Rejected, baseValid: false },
  }

  action startProbe: bool = all {
    s.phase == Idle,
    s' = {
      ...s,
      phase: Requesting,
      kind: Probe,
      baseValid: true,
      apiCredentialAttached: false,
      signedStorageCredentialAttached: false,
    },
  }

  action startStorageGet: bool = all {
    s.phase == Idle,
    s' = {
      ...s,
      phase: Requesting,
      kind: StorageGet,
      baseValid: true,
      apiCredentialAttached: false,
      signedStorageCredentialAttached: true,
    },
  }

  action startStoragePut: bool = all {
    s.phase == Idle,
    s' = {
      ...s,
      phase: Requesting,
      kind: StoragePut,
      baseValid: true,
      apiCredentialAttached: false,
      signedStorageCredentialAttached: true,
    },
  }

  action rejectRedirect: bool = all {
    s.phase == Requesting,
    s' = { ...s, phase: Rejected, redirectFollowed: false },
  }

  action succeedProbe: bool = all {
    s.phase == Requesting,
    s.kind == Probe,
    s' = {
      ...s,
      phase: Succeeded,
      bodyBytes: PROBE_SUCCESS_MAX_BYTES,
      objectJson: true,
    },
  }

  action rejectProbeOversize: bool = all {
    s.phase == Requesting,
    s.kind == Probe,
    s' = {
      ...s,
      phase: Rejected,
      bodyBytes: PROBE_SUCCESS_MAX_BYTES + 1,
      objectJson: true,
    },
  }

  action rejectProbeScalar: bool = all {
    s.phase == Requesting,
    s.kind == Probe,
    s' = {
      ...s,
      phase: Rejected,
      bodyBytes: 128,
      objectJson: false,
    },
  }

  action succeedStorage: bool = all {
    s.phase == Requesting,
    Set(StorageGet, StoragePut).contains(s.kind),
    not(s.apiCredentialAttached),
    s.signedStorageCredentialAttached,
    s' = { ...s, phase: Succeeded, transferWithinBound: true },
  }

  action rejectStorageOverflow: bool = all {
    s.phase == Requesting,
    Set(StorageGet, StoragePut).contains(s.kind),
    s' = { ...s, phase: Rejected, transferWithinBound: false },
  }

  action stutter: bool = s' = s

  action step: bool = any {
    rejectInvalidBase,
    startProbe,
    startStorageGet,
    startStoragePut,
    rejectRedirect,
    succeedProbe,
    rejectProbeOversize,
    rejectProbeScalar,
    succeedStorage,
    rejectStorageOverflow,
    stutter,
  }

  val safety: bool = and {
    not(s.redirectFollowed),
    s.phase != Succeeded or s.baseValid,
    s.phase != Succeeded or s.kind != Probe or and {
      s.bodyBytes >= 0,
      s.bodyBytes <= PROBE_SUCCESS_MAX_BYTES,
      s.objectJson,
    },
    not(Set(StorageGet, StoragePut).contains(s.kind)) or
      not(Set(Requesting, Succeeded).contains(s.phase)) or and {
        not(s.apiCredentialAttached),
        s.signedStorageCredentialAttached,
      },
    s.phase != Succeeded or
      not(Set(StorageGet, StoragePut).contains(s.kind)) or s.transferWithinBound,
  }

  val probe_success_reachable: bool =
    s.phase == Succeeded and s.kind == Probe and s.bodyBytes == PROBE_SUCCESS_MAX_BYTES

  val storage_success_reachable: bool =
    s.phase == Succeeded and Set(StorageGet, StoragePut).contains(s.kind)

  val redirect_rejection_reachable: bool =
    s.phase == Rejected and not(s.redirectFollowed)
}
