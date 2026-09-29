#![allow(clippy::needless_return)]

use std::collections::{HashSet, VecDeque};

#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
struct State {
    mask: u8,
    high: i8,
}

fn apply(state: State, chunk: u8) -> State {
    let bit = 1u8 << chunk;

    if state.mask & bit != 0 {
        return state;
    }

    return State {
        mask: state.mask | bit,
        high: state.high.max(chunk as i8),
    };
}

fn validate_transition(previous: State, next: State) -> Result<(), &'static str> {
    if next.high < previous.high {
        return Err("chunk high-watermark regressed");
    }

    if next.mask | previous.mask != next.mask {
        return Err("received chunk set regressed");
    }

    return Ok(());
}

fn run_model() -> Result<(usize, usize), &'static str> {
    let initial = State { mask: 0, high: -1 };
    let mut queue = VecDeque::from([initial]);
    let mut seen = HashSet::from([initial]);
    let mut edges = 0usize;

    while let Some(state) = queue.pop_front() {
        for chunk in 0u8..3 {
            let next = apply(state, chunk);
            edges += 1;
            validate_transition(state, next)?;

            if seen.insert(next) {
                queue.push_back(next);
            }
        }
    }

    let duplicate_state = State { mask: 1, high: 0 };
    if apply(duplicate_state, 0) != duplicate_state {
        return Err("duplicate chunk not idempotent");
    }

    return Ok((seen.len(), edges));
}

fn main() {
    match run_model() {
        Ok((states, transitions)) => {
            println!("audio chunk model: {states} states, {transitions} transitions");
            return;
        }
        Err(message) => {
            eprintln!("audio chunk model failed: {message}");
            std::process::exit(1);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{apply, run_model, State};

    #[test]
    fn explores_complete_three_chunk_state_space() {
        let (states, transitions) = run_model().expect("bounded model must satisfy invariants");
        assert_eq!(states, 8);
        assert_eq!(transitions, 24);
        return;
    }

    #[test]
    fn duplicate_chunk_is_idempotent() {
        let state = State { mask: 1, high: 0 };
        assert_eq!(apply(state, 0), state);
        return;
    }

    #[test]
    fn out_of_order_arrival_never_regresses_high_watermark() {
        let initial = State { mask: 0, high: -1 };
        let after_two = apply(initial, 2);
        let after_zero = apply(after_two, 0);
        assert_eq!(after_two.high, 2);
        assert_eq!(after_zero.high, 2);
        assert_eq!(after_zero.mask, 0b101);
        return;
    }
}
