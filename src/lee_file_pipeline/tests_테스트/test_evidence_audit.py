import json
import subprocess
import sys
from pathlib import Path

import pytest

from lee_file_pipeline.evidence_audit import audit_graph


def test_group_source_refs_distinguishes_same_page_in_different_documents():
    from lee_file_pipeline.evidence_audit import group_source_refs

    rows = [
        {'node_id': 'b', 'doc_sha256': 'a' * 64, 'page_no': 2, 'start_pos': 1, 'end_pos': 3, 'quote_status': 'located'},
        {'node_id': 'b', 'doc_sha256': 'b' * 64, 'page_no': 2, 'start_pos': 4, 'end_pos': 6, 'quote_status': 'located'},
        {'node_id': 'b', 'doc_sha256': '', 'page_no': 2, 'start_pos': 1, 'end_pos': 3, 'quote_status': 'located'},
    ]
    result = group_source_refs(rows)
    assert [(r['doc_sha256'], r['page_no'], r['row_indexes']) for r in result['groups']] == [
        ('a' * 64, 2, [0]), ('b' * 64, 2, [1])]
    assert result['unresolved'] == [{'row_index': 2, 'reason': 'invalid_or_missing_location'}]


def test_group_source_refs_preserves_each_position_and_unlocated_reason():
    from lee_file_pipeline.evidence_audit import group_source_refs

    rows = [
        {'node_id': 'b', 'doc_sha256': 'a' * 64, 'page_no': '1', 'start_pos': '1', 'end_pos': '3', 'quote_status': 'located'},
        {'node_id': 'b', 'doc_sha256': 'a' * 64, 'page_no': '1', 'start_pos': '5', 'end_pos': '7', 'quote_status': 'located'},
        {'node_id': 'b', 'quote_status': 'ambiguous'},
    ]
    result = group_source_refs(rows)
    assert result['groups'][0]['locations'] == [
        {'row_index': 0, 'node_id': 'b', 'edge_id': None, 'start_pos': 1, 'end_pos': 3},
        {'row_index': 1, 'node_id': 'b', 'edge_id': None, 'start_pos': 5, 'end_pos': 7}]
    assert result['unresolved'] == [{'row_index': 2, 'reason': 'ambiguous'}]


def test_group_source_refs_rejects_invalid_target_or_position_without_losing_rows():
    from lee_file_pipeline.evidence_audit import group_source_refs

    base = {'node_id': 'b', 'doc_sha256': 'a' * 64, 'page_no': 1,
            'start_pos': 1, 'end_pos': 3, 'quote_status': 'located'}
    rows = [{**base, 'edge_id': 'e'}, {**base, 'page_no': True},
            {**base, 'start_pos': 4}, {**base, 'quote_status': 'missing'}, {}]
    result = group_source_refs(rows)
    assert result['groups'] == []
    assert [row['reason'] for row in result['unresolved']] == [
        'invalid_or_missing_location', 'invalid_or_missing_location', 'invalid_or_missing_location',
        'missing', 'unknown_status']


def test_cli_source_refs_reports_groups_and_unresolved_without_modifying_input(tmp_path):
    path = tmp_path / 'graph.json'
    graph = {'evidence': [
        {'node_id': 'b', 'doc_sha256': 'a' * 64, 'page_no': 2, 'start_pos': 1, 'end_pos': 3, 'quote_status': 'located'},
        {'edge_id': 'e', 'quote_status': 'missing'},
    ]}
    path.write_text(json.dumps(graph), encoding='utf-8')
    original = path.read_bytes()
    result = subprocess.run([sys.executable, '-m', 'lee_file_pipeline.evidence_audit', '--source-refs', str(path)],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 2
    report = json.loads(result.stdout)
    assert report['groups'][0]['doc_sha256'] == 'a' * 64
    assert report['unresolved'] == [{'row_index': 1, 'reason': 'missing'}]
    assert path.read_bytes() == original


def test_cli_source_refs_csv_rejects_missing_headers(tmp_path):
    path = tmp_path / 'evidence.csv'
    path.write_text('doc_sha256,page_no\nabc,1\n', encoding='utf-8')
    result = subprocess.run([sys.executable, '-m', 'lee_file_pipeline.evidence_audit', '--source-refs-csv', str(path)],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 2
    assert 'missing required columns' in result.stderr
    assert not result.stdout


def test_offer_review_preview_preserves_candidates_and_does_not_change_input():
    from copy import deepcopy
    from lee_file_pipeline.evidence_audit import preview_offer_reviews

    edges = [{'id': 'e1', 'source': 'c1', 'target': 'b1', 'type': 'OFFERS', 'origin': 'document_index'},
             {'id': 'e2', 'source': 'c2', 'target': 'b1', 'type': 'OFFERS', 'origin': 'document_index'},
             {'id': 'e3', 'source': 'c3', 'target': 'b2', 'type': 'OFFERS'}]
    reviews = [{'edge_id': 'e1', 'source': 'c1', 'target': 'b1', 'decision': 'supported',
                'reviewer': 'synthetic-reviewer', 'reviewed_at': '2026-11-08T12:00:00+09:00',
                'doc_sha256': 'a' * 64, 'page_no': 2}]
    original = deepcopy(edges)
    preview = preview_offer_reviews(edges, reviews)
    assert [(item['edge_id'], item['status']) for item in preview] == [
        ('e1', 'review_recorded'), ('e2', 'candidate'), ('e3', 'unknown')]
    assert edges == original


@pytest.mark.parametrize('change', [
    {'source': 'other'}, {'reviewer': ''}, {'doc_sha256': 'bad'}, {'page_no': 0},
    {'reviewed_at': 'not-a-date'}, {'reviewed_at': '2026-11-08T12:00:00'}, {'decision': 'verified'},
])
def test_offer_review_preview_rejects_invalid_or_mismatched_records(change):
    from lee_file_pipeline.evidence_audit import preview_offer_reviews

    edges = [{'id': 'e1', 'source': 'c1', 'target': 'b1', 'type': 'OFFERS'}]
    review = {'edge_id': 'e1', 'source': 'c1', 'target': 'b1', 'decision': 'supported',
              'reviewer': 'synthetic-reviewer', 'reviewed_at': '2026-11-08T12:00:00+09:00',
              'doc_sha256': 'a' * 64, 'page_no': 2}
    review.update(change)
    with pytest.raises(ValueError):
        preview_offer_reviews(edges, [review])


def test_offer_review_preview_rejects_duplicate_reviews():
    from lee_file_pipeline.evidence_audit import preview_offer_reviews

    edges = [{'id': 'e1', 'source': 'c1', 'target': 'b1', 'type': 'OFFERS'}]
    review = {'edge_id': 'e1', 'source': 'c1', 'target': 'b1', 'decision': 'supported',
              'reviewer': 'synthetic-reviewer', 'reviewed_at': '2026-11-08T12:00:00+09:00',
              'doc_sha256': 'a' * 64, 'page_no': 2}
    with pytest.raises(ValueError):
        preview_offer_reviews(edges, [review, review])


@pytest.mark.parametrize('decision', ['not_supported', 'uncertain'])
def test_offer_review_preview_preserves_nonaffirmative_decisions(decision):
    from lee_file_pipeline.evidence_audit import preview_offer_reviews

    edges = [{'id': 'e1', 'source': 'c1', 'target': 'b1', 'type': 'OFFERS'}]
    review = {'edge_id': 'e1', 'source': 'c1', 'target': 'b1', 'decision': decision,
              'reviewer': 'synthetic-reviewer', 'reviewed_at': '2026-11-08T12:00:00+09:00',
              'doc_sha256': 'a' * 64, 'page_no': 2}
    assert preview_offer_reviews(edges, [review])[0] == {
        'edge_id': 'e1', 'status': 'review_recorded', 'decision': decision}


def test_detects_missing_edge_despite_unchanged_evidence_count():
    report = audit_graph({'edges': [{'_fp_id': 'e1'}], 'evidence': [{'edge_id': 'e1'}, {'edge_id': 'e2'}]})
    assert report['status'] == 'findings'
    assert report['evidence_count'] == 2
    assert report['dangling_edge_ids'] == ['e2']


def test_accepts_both_id_forms_and_node_evidence():
    report = audit_graph({'edges': [{'id': 'uuid', '_fp_id': 'original'}], 'evidence': [{'edge_id': 'original'}, {'edge_id': 'uuid'}, {'node_id': 'n1'}]})
    assert report['status'] == 'ok'
    assert report['node_evidence_count'] == 1


def test_missing_edge_identity_makes_missing_reference_inconclusive():
    report = audit_graph({'edges': [{'source': 'a', 'target': 'b'}], 'evidence': [{'edge_id': 'e2'}]})
    assert report['status'] == 'incomplete'
    assert report['dangling_edge_ids'] == []
    assert report['unresolved_edge_ids'] == ['e2']


def test_duplicate_ids_and_unbound_evidence_are_reported():
    report = audit_graph({'edges': [{'id': 'e1'}, {'_fp_id': 'e1'}], 'evidence': [{}]})
    assert report['status'] == 'findings'
    assert report['duplicate_edge_ids'] == ['e1']
    assert report['unbound_evidence_count'] == 1


@pytest.mark.parametrize('graph', [{}, {'edges': [], 'evidence': [1]}, {'edges': 'x', 'evidence': []}])
def test_invalid_input_is_rejected(graph):
    with pytest.raises(ValueError):
        audit_graph(graph)


def test_cli_reads_json_and_reports_exit_code(tmp_path):
    path = tmp_path / 'graph.json'
    path.write_text(json.dumps({'edges': [{'id': 'e1'}], 'evidence': [{'edge_id': 'missing'}]}), encoding='utf-8')
    result = subprocess.run([sys.executable, '-m', 'lee_file_pipeline.evidence_audit', str(path)], capture_output=True, text=True, check=False)
    assert result.returncode == 1
    assert json.loads(result.stdout)['dangling_edge_ids'] == ['missing']


def test_ambiguous_target_and_incomplete_reference_are_both_visible():
    report = audit_graph({'edges': [{}], 'evidence': [{'node_id': 'n1', 'edge_id': 'e1'}, {'edge_id': 'e2'}]})
    assert report['status'] == 'findings'
    assert report['ambiguous_evidence_count'] == 1
    assert report['unresolved_edge_ids'] == ['e2']


def test_cli_incomplete_and_invalid_input(tmp_path):
    path = tmp_path / 'graph.json'
    path.write_text(json.dumps({'edges': [{}], 'evidence': [{'edge_id': 'e2'}]}), encoding='utf-8')
    cmd = [sys.executable, '-m', 'lee_file_pipeline.evidence_audit', str(path)]
    incomplete = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert incomplete.returncode == 2
    assert json.loads(incomplete.stdout)['status'] == 'incomplete'
    path.write_text('{', encoding='utf-8')
    invalid = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert invalid.returncode == 2
    assert 'Input error:' in invalid.stderr


def test_existing_deduper_reconnects_reference():
    from payment_card.file_pipeline.chat.retrieval.entity_dedupe import dedupe_subgraph

    graph = {
        'nodes': [{'id': 'a'}, {'id': 'b'}, {'id': 't'}],
        'edges': [
            {'_fp_id': 'e1', 'source': 'a', 'target': 't', 'type': 'OFFERS'},
            {'_fp_id': 'e2', 'source': 'b', 'target': 't', 'type': 'OFFERS'},
        ],
        'evidence': [{'edge_id': 'e1'}, {'edge_id': 'e2'}],
        'seeds': ['a', 'b'],
    }
    report = audit_graph(dedupe_subgraph(graph, {'b': 'a'}))
    assert report['dangling_edge_ids'] == []


def test_duplicate_edge_evidence_should_reference_surviving_edge():
    from payment_card.file_pipeline.chat.retrieval.entity_dedupe import dedupe_subgraph

    graph = {
        'nodes': [{'id': 'a'}, {'id': 'b'}, {'id': 't'}],
        'edges': [{'_fp_id': 'e1', 'source': 'a', 'target': 't', 'type': 'OFFERS'},
                  {'_fp_id': 'e2', 'source': 'b', 'target': 't', 'type': 'OFFERS'}],
        'evidence': [{'_probe_evidence_id': '0', 'edge_id': 'e1'},
                     {'_probe_evidence_id': '1', 'edge_id': 'e2'}],
    }
    result = dedupe_subgraph(graph, {'b': 'a'})
    assert len(result['evidence']) == 2
    assert audit_graph(result)['dangling_edge_ids'] == []


def test_self_loop_evidence_should_be_retained_separately():
    from payment_card.file_pipeline.chat.retrieval.entity_dedupe import dedupe_subgraph

    graph = {'nodes': [{'id': 'a'}, {'id': 'b'}],
             'edges': [{'_fp_id': 'e1', 'source': 'a', 'target': 'b', 'type': 'OFFERS'}],
             'evidence': [{'_probe_evidence_id': '0', 'edge_id': 'e1'}]}
    result = dedupe_subgraph(graph, {'b': 'a'})
    assert result.get('unresolved_edge_evidence') == [
        {'reason': 'removed_self_loop', 'evidence': graph['evidence'][0]}
    ]
    assert not result['evidence']


def test_duplicate_representative_is_stable_and_preserves_both_id_namespaces():
    from payment_card.file_pipeline.chat.retrieval.entity_dedupe import dedupe_subgraph

    first = {'id': 'uuid-z', '_fp_id': 'fp-z', 'source': 'a', 'target': 't', 'type': 'OFFERS'}
    second = {'id': 'uuid-a', '_fp_id': 'fp-a', 'source': 'b', 'target': 't', 'type': 'OFFERS'}
    graph = {'nodes': [{'id': 'a'}, {'id': 'b'}, {'id': 't'}], 'edges': [first, second],
             'evidence': [{'edge_id': 'uuid-z'}, {'edge_id': 'fp-z'}]}
    forward = dedupe_subgraph(graph, {'b': 'a'})
    reverse = dedupe_subgraph({**graph, 'edges': [second, first]}, {'b': 'a'})
    assert forward['edges'] == reverse['edges']
    assert {e['edge_id'] for e in forward['evidence']} == {'uuid-a', 'fp-a'}
    assert audit_graph(forward)['status'] == 'ok'


def test_unidentified_edge_is_not_discarded_when_referenced_duplicate_cannot_map():
    from payment_card.file_pipeline.chat.retrieval.entity_dedupe import dedupe_subgraph

    graph = {'nodes': [{'id': 'a'}, {'id': 'b'}, {'id': 't'}],
             'edges': [{'source': 'a', 'target': 't', 'type': 'OFFERS'},
                       {'_fp_id': 'e2', 'source': 'b', 'target': 't', 'type': 'OFFERS'}],
             'evidence': [{'edge_id': 'e2'}]}
    result = dedupe_subgraph(graph, {'b': 'a'})
    assert audit_graph(result)['dangling_edge_ids'] == []
    assert any(e.get('_fp_id') == 'e2' for e in result['edges'])


def test_ambiguous_edge_identifiers_fail_without_mutating_input():
    from copy import deepcopy
    from payment_card.file_pipeline.chat.retrieval.entity_dedupe import dedupe_subgraph

    graph = {'nodes': [{'id': 'a'}, {'id': 'b'}, {'id': 't'}],
             'edges': [{'_fp_id': 'same', 'source': 'a', 'target': 't', 'type': 'OFFERS'},
                       {'_fp_id': 'same', 'source': 'b', 'target': 't', 'type': 'OFFERS'}],
             'evidence': [{'edge_id': 'same'}]}
    original = deepcopy(graph)
    with pytest.raises(ValueError, match='ambiguous edge identifier'):
        dedupe_subgraph(graph, {'b': 'a'})
    assert graph == original


def test_probe_reports_quarantined_self_loop_evidence():
    from payment_card.file_pipeline.chat.eval.entity_dup_probe import evaluate_question

    class Matcher:
        def select(self, question, n=3, threshold=0.15):
            return ['Synthetic Card']

    nodes = [{'id': 'a', 'name': 'Synthetic Card', 'label': 'Card', 'props': {}},
             {'id': 'b', 'name': 'Synthetic benefit', 'label': 'Benefit', 'props': {}}]
    edges = [{'_fp_id': 'e1', 'source': 'a', 'target': 'b', 'type': 'OFFERS'}]
    evidence = [{'edge_id': 'e1', 'node_id': '', 'doc_sha256': 'synthetic', 'page_no': '1'}]
    row = evaluate_question({'id': 'SYN', 'question': 'Synthetic Card'}, nodes, edges, evidence, Matcher(), {'b': 'a'}, {})
    assert row['evidence_count_before'] == 1
    assert row['evidence_count_after'] == 0
    assert row['unresolved_edge_evidence_count'] == 1
    assert row['evidence_preservation_violation'] == 0


def test_probe_reports_reconnected_duplicate_evidence():
    from payment_card.file_pipeline.chat.eval.entity_dup_probe import evaluate_question, summarize

    class Matcher:
        def select(self, question, n=3, threshold=0.15):
            return ['Synthetic Card']

    nodes = [{'id': 't', 'name': 'Synthetic Card', 'label': 'Card', 'props': {}},
             {'id': 'a', 'name': 'A', 'label': 'Benefit', 'props': {}},
             {'id': 'b', 'name': 'B', 'label': 'Benefit', 'props': {}}]
    edges = [{'_fp_id': 'e1', 'source': 't', 'target': 'a', 'type': 'OFFERS'},
             {'_fp_id': 'e2', 'source': 't', 'target': 'b', 'type': 'OFFERS'}]
    evidence = [{'edge_id': 'e1', 'node_id': '', 'doc_sha256': 'synthetic-a'},
                {'edge_id': 'e2', 'node_id': '', 'doc_sha256': 'synthetic-b'}]
    row = evaluate_question({'id': 'SYN', 'question': 'Synthetic Card'}, nodes, edges, evidence, Matcher(), {'b': 'a'}, {})
    assert row['evidence_count_before'] == row['evidence_count_after'] == 2
    assert row['dangling_edge_evidence_count'] == 0
    assert row['unresolved_edge_evidence_count'] == 0
    assert row['evidence_preservation_violation'] == 0
    assert summarize([row])['dangling_edge_evidence_count'] == 0


def test_graph_without_edge_evidence_keeps_legacy_first_edge_behavior():
    from payment_card.file_pipeline.chat.retrieval.entity_dedupe import dedupe_subgraph

    graph = {'nodes': [{'id': 'a'}, {'id': 'b'}, {'id': 't'}],
             'edges': [{'source': 'a', 'target': 't', 'type': 'OFFERS', 'label': 'first'},
                       {'source': 'b', 'target': 't', 'type': 'OFFERS', 'label': 'second'}],
             'seeds': ['a']}
    result = dedupe_subgraph(graph, {'b': 'a'})
    assert result['edges'] == [{'source': 'a', 'target': 't', 'type': 'OFFERS', 'label': 'first'}]
    assert 'unresolved_edge_evidence' not in result


def test_audit_reports_preserved_self_loop_evidence_as_finding():
    from payment_card.file_pipeline.chat.retrieval.entity_dedupe import dedupe_subgraph

    graph = {'nodes': [{'id': 'a'}, {'id': 'b'}],
             'edges': [{'_fp_id': 'e1', 'source': 'a', 'target': 'b', 'type': 'OFFERS'}],
             'evidence': [{'edge_id': 'e1'}]}
    report = audit_graph(dedupe_subgraph(graph, {'b': 'a'}))
    assert report['status'] == 'findings'
    assert report['unresolved_edge_evidence_count'] == 1
    assert report['dangling_edge_ids'] == []
