import unittest

from deep_tests.contract_model import Command, IdempotencyConflict, ReferenceStore, generate_valid_trace, replay


class SonusDomainHardeningTests(unittest.TestCase):
    def test_duplicate_audio_segment_commit_is_exactly_once(self) -> None:
        store = ReferenceStore()
        segment = Command("create", "segment-000042", "fft-window-v1", "segment-42")
        first = store.apply(segment)
        revision = store.revision
        for _ in range(48):
            self.assertEqual(store.apply(segment), first)
        self.assertEqual(store.revision, revision)

    def test_segment_idempotency_key_cannot_change_payload(self) -> None:
        store = ReferenceStore()
        store.apply(Command("create", "segment-000042", "fft-window-v1", "segment-stable"))
        with self.assertRaises(IdempotencyConflict):
            store.apply(Command("update", "segment-000042", "fft-window-v2", "segment-stable"))

    def test_rolling_audio_trace_converges_under_duplicate_delivery(self) -> None:
        commands = generate_valid_trace(2026091402, steps=840)
        snapshots = {replay(commands, duplicate_every=n).snapshot() for n in (2, 5, 11, 19)}
        self.assertEqual(len(snapshots), 1)


if __name__ == "__main__":
    unittest.main()
