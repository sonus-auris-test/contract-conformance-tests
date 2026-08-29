import unittest

from deep_tests.presence_model import Effect, Input, Phase, State, advance


class PresenceLifecycleContractTests(unittest.TestCase):
    def test_stale_callbacks_stutter_after_replacement_and_close(self) -> None:
        first = advance(State(), Input.CONFIGURE).state
        replacement = advance(first, Input.CONFIGURE).state

        for input_ in Input:
            if input_ in {Input.CONFIGURE, Input.CLOSE}:
                continue
            stale = advance(replacement, input_, first.generation)
            self.assertEqual(stale.state, replacement, input_.value)
            self.assertEqual(stale.effects, (), input_.value)

        closed = advance(replacement, Input.CLOSE).state
        self.assertEqual(closed.phase, Phase.CLOSED)
        for input_ in Input:
            if input_ in {Input.CONFIGURE, Input.CLOSE}:
                continue
            stale = advance(closed, input_, replacement.generation)
            self.assertEqual(stale.state, closed, input_.value)
            self.assertEqual(stale.effects, (), input_.value)

    def test_authentication_and_retry_effects_are_phase_scoped(self) -> None:
        connecting = advance(State(), Input.CONFIGURE).state
        authenticating = advance(
            connecting,
            Input.TRANSPORT_READY,
            connecting.generation,
        )
        self.assertEqual(authenticating.state.phase, Phase.AUTHENTICATING)
        self.assertEqual(authenticating.effects, (Effect.SEND_AUTHENTICATION,))

        connected = advance(
            authenticating.state,
            Input.AUTHENTICATED,
            authenticating.state.generation,
        )
        self.assertEqual(connected.state.phase, Phase.CONNECTED)
        self.assertEqual(connected.effects, (Effect.START_HEARTBEAT,))

        waiting = advance(
            connected.state,
            Input.TRANSPORT_FAILED,
            connected.state.generation,
        )
        self.assertEqual(waiting.state.phase, Phase.WAITING_TO_RETRY)
        self.assertEqual(
            waiting.effects,
            (Effect.CLOSE_TRANSPORT, Effect.SCHEDULE_RECONNECT),
        )
        self.assertEqual(waiting.state.reconnect_delay_seconds, 1)

    def test_bounded_graph_is_total_deterministic_and_invariant_safe(self) -> None:
        frontier = [State()]
        seen = {State()}

        for _depth in range(12):
            layer, frontier = frontier, []
            for state in layer:
                self.assertTrue(state.valid, state)
                for input_ in Input:
                    generations = (
                        (None,)
                        if input_ in {Input.CONFIGURE, Input.CLOSE}
                        else (
                            None,
                            state.generation - 1,
                            state.generation,
                            state.generation + 1,
                        )
                    )
                    for generation in generations:
                        first = advance(state, input_, generation)
                        second = advance(state, input_, generation)
                        self.assertEqual(first, second)
                        self.assertTrue(first.state.valid, first)
                        if (
                            input_ not in {Input.CONFIGURE, Input.CLOSE}
                            and generation != state.generation
                        ):
                            self.assertEqual(first.state, state)
                            self.assertEqual(first.effects, ())
                        if first.state.generation <= 12 and first.state not in seen:
                            seen.add(first.state)
                            frontier.append(first.state)

        self.assertGreater(len(seen), 40)

    def test_backoff_is_monotone_and_capped(self) -> None:
        state = advance(State(), Input.CONFIGURE).state
        delays: list[int] = []
        for _attempt in range(9):
            state = advance(
                state,
                Input.TRANSPORT_FAILED,
                state.generation,
            ).state
            delays.append(state.reconnect_delay_seconds)
            state = advance(state, Input.RETRY_TIMER, state.generation).state

        self.assertEqual(delays, [1, 2, 4, 8, 16, 32, 60, 60, 60])


if __name__ == "__main__":
    unittest.main()
