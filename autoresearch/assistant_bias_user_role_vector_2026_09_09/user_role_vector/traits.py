"""Assistant-trait names from Table 17."""

ASSISTANT_TRAITS: tuple[str, ...] = (
    "cooperative",
    "helpful",
    "compliant",
    "sycophantic",
    "polite",
    "patient",
    "structured",
    "explicit",
    "complete",
    "verbose",
    "fluent",
    "generic",
    "neutral",
    "consistent",
    "rational",
    "goal_aligned",
    "accommodating",
    "deferential",
    "explanatory",
    "selfless",
)

# Paper text: these four traits point toward the user direction.
USER_ALIGNED_TRAITS: frozenset[str] = frozenset(
    {"explicit", "deferential", "generic", "patient"}
)
