"""Pure waiting-candidate choice; resource checks remain in Scheduler."""

POLICIES = ("baseline", "short_prompt", "aged_short_prompt")
AGING_RATE_TOKENS_PER_SECOND = 320
NS_PER_SECOND = 1_000_000_000


def validate_policy(policy):
    if type(policy) is not str or policy not in POLICIES:
        raise ValueError(f"invalid scheduling_policy {policy!r}; expected one of {POLICIES}")
    return policy


def validate_aging_rate(rate):
    if type(rate) is not int or rate != AGING_RATE_TOKENS_PER_SECOND:
        raise ValueError(f"invalid aging_rate_tokens_per_second {rate!r}; "
                         f"expected {AGING_RATE_TOKENS_PER_SECOND}")
    return rate


def aging_score_ns(prompt_tokens, first_enqueue_ns, now_ns,
                   aging_rate_tokens_per_second=AGING_RATE_TOKENS_PER_SECOND):
    """Token-equivalent priority scaled by nanoseconds, using first-enqueue age."""
    age_ns = max(0, now_ns - first_enqueue_ns)
    return prompt_tokens * NS_PER_SECOND - aging_rate_tokens_per_second * age_ns


def choose_waiting_index(waiting, policy, *, now_ns=None, first_enqueue_ns=None,
                         aging_rate_tokens_per_second=AGING_RATE_TOKENS_PER_SECOND):
    """Return the leftmost minimum-priority candidate, without mutation."""
    validate_policy(policy)
    if not waiting:
        raise ValueError("cannot select from an empty waiting deque")
    if policy == "baseline":
        return 0
    if policy == "aged_short_prompt":
        validate_aging_rate(aging_rate_tokens_per_second)
        if now_ns is None or first_enqueue_ns is None:
            raise ValueError("aged_short_prompt requires now_ns and first_enqueue_ns")
    best_index = 0
    best_score = None
    for index, seq in enumerate(waiting):
        score = (aging_score_ns(seq.num_prompt_tokens, first_enqueue_ns[seq.seq_id],
                                  now_ns, aging_rate_tokens_per_second)
                 if policy == "aged_short_prompt" else seq.num_prompt_tokens)
        if best_score is None or score < best_score:
            best_index = index
            best_score = score
    return best_index
