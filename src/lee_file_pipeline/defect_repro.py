"""Reproduce current relationship/source issues using synthetic data only."""
from __future__ import annotations

import json

from payment_card.file_pipeline.chat.retrieval.entity_dedupe import dedupe_subgraph
from payment_card.file_pipeline.chat.ui.ui_v2 import collect_sources
from payment_card.file_pipeline.chat.eval.entity_dup_probe import summarize


def run() -> dict:
    # A mapped representative need not be in the retrieved subgraph.
    graph = {'nodes': [{'id': 'b', 'props': {}}, {'id': 't', 'props': {}}],
             'edges': [{'source': 'b', 'target': 't', 'type': 'OFFERS'}],
             'evidence': [{'node_id': 'b'}], 'seeds': ['b']}
    result = dedupe_subgraph(graph, {'b': 'a'})
    node_ids = {node['id'] for node in result['nodes']}
    missing = sorted({result['edges'][0]['source'], result['evidence'][0]['node_id'], result['seeds'][0]} - node_ids)

    # The pipeline stores source_text_pages as comma-separated text.
    page_graph = {'nodes': [
        {'id': 'a', 'name': 'synthetic', 'label': 'Benefit', 'props': {'source_text': 'SYN-A', 'source_text_pages': '2,3'}},
        {'id': 'b', 'name': 'synthetic', 'label': 'Benefit', 'props': {'source_text': 'SYN-B', 'source_text_pages': '4,5'}},
    ], 'edges': []}
    pages = dedupe_subgraph(page_graph, {'b': 'a'})['nodes'][0]['props']['source_text_pages']

    # Merged member text and its page must stay paired in the display.
    single_pages = {'nodes': [
        {'id': 'a', 'name': 'synthetic', 'label': 'Benefit', 'props': {'source_text': 'SYN-A', 'source_text_pages': '2'}},
        {'id': 'b', 'name': 'synthetic', 'label': 'Benefit', 'props': {'source_text': 'SYN-B', 'source_text_pages': '3'}},
    ], 'edges': []}
    merged = dedupe_subgraph(single_pages, {'b': 'a'})
    shown = [row for row in collect_sources(merged) if row['title'] != '안내']

    # A connected subgraph may contain a second benefit reached through a shared node.
    scope = {'nodes': [
        {'id': 'c1', 'label': 'Card', 'name': 'synthetic-card-A', 'props': {}},
        {'id': 'b1', 'label': 'Benefit', 'name': 'synthetic-benefit-A', 'props': {}},
        {'id': 'b2', 'label': 'Benefit', 'name': 'synthetic-benefit-B', 'props': {}},
        {'id': 't', 'label': 'Target', 'name': 'synthetic-target', 'props': {}},
    ], 'edges': [{'source': 'c1', 'target': 'b1', 'type': 'OFFERS'},
                 {'source': 'b1', 'target': 't', 'type': 'APPLIES_TO'},
                 {'source': 'b2', 'target': 't', 'type': 'APPLIES_TO'}], 'seeds': ['c1']}
    titles = [row['title'] for row in collect_sources(scope) if row['title'] != '안내']

    # Earlier result rows do not contain the newly added summary keys.
    legacy_row = {'nodes_reduced': 0, 'node_count_before': 1,
                  'evidence_preservation_violation': 0, 'golden_evidence_affected': 0}
    try:
        summarize([legacy_row])
        legacy_result = 'accepted'
    except KeyError as exc:
        legacy_result = f'missing field: {exc.args[0]}'

    chain = {'nodes': [{'id': value} for value in ('a', 'b', 'c', 't')],
             'edges': [{'_fp_id': 'e0', 'source': 'c', 'target': 't', 'type': 'OFFERS'},
                       {'_fp_id': 'e1', 'source': 'a', 'target': 't', 'type': 'OFFERS'},
                       {'_fp_id': 'e2', 'source': 'b', 'target': 't', 'type': 'OFFERS'}],
             'evidence': [{'edge_id': 'e2'}]}
    first = dedupe_subgraph(chain, {'b': 'a'})
    try:
        dedupe_subgraph(first, {'a': 'c'})
        chain_result = 'accepted'
    except ValueError as exc:
        chain_result = str(exc)

    return {
        'representative_absent': {'node_ids': sorted(node_ids), 'invalid_references': missing,
                                  'expected_invalid_references': []},
        'comma_separated_pages': {'input_pages': ['2,3', '4,5'], 'output_pages': pages,
                                  'expected_pages': [2, 3, 4, 5]},
        'merged_source_display': {'stored_source_count': len(merged['nodes'][0]['sources']),
                                  'displayed': [{'text': row['text'], 'pages': row['pages']} for row in shown],
                                  'expected': [{'text': 'SYN-A', 'pages': [2]}, {'text': 'SYN-B', 'pages': [3]}]},
        'selected_card_source_scope': {'selected_seed': 'c1', 'displayed_benefits': titles},
        'legacy_summary_row': {'result': legacy_result},
        'sequential_merge': {'result': chain_result},
    }


def main() -> None:
    print(json.dumps(run(), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
