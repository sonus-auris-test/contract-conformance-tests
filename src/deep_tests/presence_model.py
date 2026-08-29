from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Phase(str, Enum):
    IDLE = "idle"
    CONNECTING = "connecting"
    AUTHENTICATING = "authenticating"
    CONNECTED = "connected"
    WAITING_TO_RETRY = "waiting_to_retry"
    CLOSED = "closed"


class Input(str, Enum):
    CONFIGURE = "configure"
    TRANSPORT_READY = "transport_ready"
    AUTHENTICATED = "authenticated"
    PRESENCE_FRAME = "presence_frame"
    HEARTBEAT_TIMER = "heartbeat_timer"
    TRANSPORT_FAILED = "transport_failed"
    RETRY_TIMER = "retry_timer"
    CLOSE = "close"


class Effect(str, Enum):
    CLOSE_TRANSPORT = "close_transport"
    OPEN_TRANSPORT = "open_transport"
    SEND_AUTHENTICATION = "send_authentication"
    START_HEARTBEAT = "start_heartbeat"
    SEND_HEARTBEAT = "send_heartbeat"
    SCHEDULE_RECONNECT = "schedule_reconnect"


@dataclass(frozen=True)
class State:
    phase: Phase = Phase.IDLE
    generation: int = 0
    retry_attempt: int = 0

    @property
    def valid(self) -> bool:
        if self.generation < 0 or not 0 <= self.retry_attempt <= 7:
            return False
        if self.phase in {Phase.IDLE, Phase.CLOSED} and self.retry_attempt != 0:
            return False
        return True

    @property
    def reconnect_delay_seconds(self) -> int:
        if self.phase is not Phase.WAITING_TO_RETRY or self.retry_attempt == 0:
            return 0
        return min(1 << min(self.retry_attempt - 1, 6), 60)


@dataclass(frozen=True)
class Transition:
    state: State
    effects: tuple[Effect, ...] = ()


def advance(
    state: State,
    input_: Input,
    event_generation: int | None = None,
) -> Transition:
    if input_ is Input.CONFIGURE:
        return Transition(
            State(Phase.CONNECTING, state.generation + 1, 0),
            (Effect.CLOSE_TRANSPORT, Effect.OPEN_TRANSPORT),
        )
    if input_ is Input.CLOSE:
        if state.phase is Phase.CLOSED:
            return Transition(state)
        return Transition(
            State(Phase.CLOSED, state.generation + 1, 0),
            (Effect.CLOSE_TRANSPORT,),
        )
    if event_generation != state.generation:
        return Transition(state)

    if input_ is Input.TRANSPORT_READY and state.phase is Phase.CONNECTING:
        return Transition(
            State(Phase.AUTHENTICATING, state.generation, state.retry_attempt),
            (Effect.SEND_AUTHENTICATION,),
        )
    if input_ is Input.AUTHENTICATED and state.phase is Phase.AUTHENTICATING:
        return Transition(
            State(Phase.CONNECTED, state.generation, 0),
            (Effect.START_HEARTBEAT,),
        )
    if input_ is Input.HEARTBEAT_TIMER and state.phase is Phase.CONNECTED:
        return Transition(state, (Effect.SEND_HEARTBEAT,))
    if input_ is Input.TRANSPORT_FAILED and state.phase in {
        Phase.CONNECTING,
        Phase.AUTHENTICATING,
        Phase.CONNECTED,
    }:
        return Transition(
            State(
                Phase.WAITING_TO_RETRY,
                state.generation + 1,
                min(state.retry_attempt + 1, 7),
            ),
            (Effect.CLOSE_TRANSPORT, Effect.SCHEDULE_RECONNECT),
        )
    if input_ is Input.RETRY_TIMER and state.phase is Phase.WAITING_TO_RETRY:
        return Transition(
            State(Phase.CONNECTING, state.generation + 1, state.retry_attempt),
            (Effect.OPEN_TRANSPORT,),
        )
    return Transition(state)
