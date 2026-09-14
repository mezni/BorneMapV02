"""Reciprocal Rank Fusion (RRF) calculation.

Merges several ranked lists into a single fused ranking using the standard
formula::

    RRF_Score(d) = sum over m in M of 1 / (k + r_m(d))

where ``r_m(d)`` is the 1-based rank of document ``d`` in list ``m`` and ``k``
is a small constant (default 60). Lists may be weighted; weights scale each
list's contribution to the final score.
"""

from __future__ import annotations

from collections.abc import Sequence


def reciprocal_rank_fusion[T](
    ranked_lists: Sequence[Sequence[T]],
    *,
    k: int = 60,
    weights: Sequence[float] | None = None,
) -> list[tuple[T, float]]:
    """Fuse ``ranked_lists`` into one list of ``(item, score)`` sorted by score.

    ``k`` controls the smoothing constant; ``weights`` optionally scales the
    contribution of each ranked list (defaults to 1.0 for every list). Items
    appearing in multiple lists accumulate score, yielding a de-duplicated,
    globally ranked result.
    """
    list_weights = weights or [1.0] * len(ranked_lists)
    if len(list_weights) != len(ranked_lists):
        msg = f"weights ({len(list_weights)}) must match ranked_lists ({len(ranked_lists)})"
        raise ValueError(msg)

    scores: dict[T, float] = {}
    for list_weight, ranked in zip(list_weights, ranked_lists, strict=True):
        for rank, item in enumerate(ranked):
            scores[item] = scores.get(item, 0.0) + list_weight / (k + rank + 1)

    return sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
