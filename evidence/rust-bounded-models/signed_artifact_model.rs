#![allow(clippy::needless_return)]

fn admitted(
    tenant_match: bool,
    token_valid: bool,
    unexpired: bool,
    digest_match: bool,
) -> bool {
    return tenant_match && token_valid && unexpired && digest_match;
}

fn run_model() -> Result<usize, &'static str> {
    let mut explored = 0usize;

    for tenant_match in [false, true] {
        for token_valid in [false, true] {
            for unexpired in [false, true] {
                for digest_match in [false, true] {
                    let expected = tenant_match && token_valid && unexpired && digest_match;
                    if admitted(tenant_match, token_valid, unexpired, digest_match) != expected {
                        return Err("signed artifact admission diverged from obligations");
                    }
                    explored += 1;
                }
            }
        }
    }

    if admitted(true, true, false, true) {
        return Err("expired artifact token admitted");
    }

    if admitted(false, true, true, true) {
        return Err("cross-tenant artifact admission allowed");
    }

    return Ok(explored);
}

fn main() {
    match run_model() {
        Ok(explored) => {
            println!("signed artifact admission: {explored} states");
            return;
        }
        Err(message) => {
            eprintln!("signed artifact admission failed: {message}");
            std::process::exit(1);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{admitted, run_model};

    #[test]
    fn explores_all_sixteen_states() {
        let explored = run_model().expect("bounded admission model must satisfy invariants");
        assert_eq!(explored, 16);
        return;
    }

    #[test]
    fn requires_all_four_obligations() {
        assert!(admitted(true, true, true, true));
        assert!(!admitted(false, true, true, true));
        assert!(!admitted(true, false, true, true));
        assert!(!admitted(true, true, false, true));
        assert!(!admitted(true, true, true, false));
        return;
    }
}
