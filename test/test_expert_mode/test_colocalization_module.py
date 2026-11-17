from collections import defaultdict

import pytest

from backend.expert_mode.modules.colocalization import derive_full_colocalization


@pytest.mark.parametrize(
    ("edges", "expected"),
    [
        # (
        #         [('a', 'b')],
        #         {frozenset(('a', 'b'))}
        # ),
        # (
        #         [('a', 'b'), ('a', 'c'), ('b', 'c')],
        #         {frozenset(('a', 'b', 'c'))},
        # ),
        # (
        #         [('a', 'b'), ('a', 'c')],
        #         {frozenset(('a', 'b')), frozenset(('a', 'c'))},
        # ),
        (
                [('a', 'b'), ('a', 'c'), ('b', 'c'), ('a', 'd'), ('b', 'd')],
                {frozenset(('a', 'b', 'c')), frozenset(('a', 'b', 'd'))},
        ),
        (
                [('a', 'b'), ('a', 'c'), ('b', 'c'), ('c', 'f'), ('b', 'd'), ('a', 'd'), ('a', 'e'), ('b', 'e'),
                 ('d', 'e')],
                {frozenset(('c', 'f')), frozenset(('a', 'b', 'c')), frozenset(('a', 'b', 'd', 'e'))},
        ),
    ],
    ids=[#'pair', 'triangle', 'branch',
         'overlapping-triangles', 'new'],
)
def test_identify_colocalizations(edges, expected):
    pairs_by_id = defaultdict(list)
    for first, second in edges:
        pairs_by_id[first].append((first, second))
        pairs_by_id[second].append((first, second))

    result = derive_full_colocalization(pairs_by_id)

    assert result is not None, 'identify_colocalizations must return the identified clusters'
    assert {frozenset(cluster) for cluster in result} == expected
