"""Pure waiting-candidate choice; resource checks remain in Scheduler."""

POLICIES = ("baseline", "short_prompt")


def validate_policy(policy):
    if type(policy) is not str or policy not in POLICIES:
        raise ValueError(f"invalid scheduling_policy {policy!r}; expected one of {POLICIES}")
    return policy


def choose_waiting_index(waiting, policy):
    """Return the leftmost minimum original prompt length, without mutation."""
    validate_policy(policy)
    if not waiting:
        raise ValueError("cannot select from an empty waiting deque")
    if policy == "baseline":
        return 0
    best_index = 0
    best_length = None
    for index, seq in enumerate(waiting):
        length = seq.num_prompt_tokens
        if best_length is None or length < best_length:
            best_index = index
            best_length = length
    return best_index
