"""Read-only integrity checks for edge references in a supplied subgraph."""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path


def _identifier(value: object) -> str | None:
    if value is None or value == '':
        return None
    if not isinstance(value, str):
        raise ValueError('identifiers must be strings or empty')
    return value


def group_source_refs(rows: list[dict]) -> dict:
    """Group supplied located evidence by document and page, without reading text.

    Unlocatable rows are returned separately; a location does not establish that
    a displayed excerpt or a card's benefit is supported by that location.
    """
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError('evidence must be an array of objects')
    groups = {}
    unresolved = []
    for index, row in enumerate(rows):
        status = row.get('quote_status')
        if status != 'located':
            unresolved.append({'row_index': index, 'reason': status if isinstance(status, str) and status in {'ambiguous', 'missing'} else 'unknown_status'})
            continue
        digest = row.get('doc_sha256')
        node_id, edge_id = row.get('node_id') or None, row.get('edge_id') or None
        try:
            numbers = [row.get(key) for key in ('page_no', 'start_pos', 'end_pos')]
            if any(isinstance(value, bool) or not str(value).isdigit() for value in numbers):
                raise ValueError
            page, start, end = map(int, numbers)
            if (not isinstance(digest, str) or not re.fullmatch(r'[0-9a-fA-F]{64}', digest)
                    or page < 1 or start < 1 or end < start
                    or bool(node_id) == bool(edge_id)
                    or any(value is not None and not isinstance(value, str) for value in (node_id, edge_id))):
                raise ValueError
        except (TypeError, ValueError):
            unresolved.append({'row_index': index, 'reason': 'invalid_or_missing_location'})
            continue
        key = (digest.lower(), page)
        group = groups.setdefault(key, {'doc_sha256': key[0], 'page_no': page, 'row_indexes': [], 'locations': []})
        group['row_indexes'].append(index)
        group['locations'].append({'row_index': index, 'node_id': node_id, 'edge_id': edge_id,
                                   'start_pos': start, 'end_pos': end})
    return {'groups': [groups[key] for key in sorted(groups)], 'unresolved': unresolved}


def preview_offer_reviews(edges: list[dict], reviews: list[dict]) -> list[dict]:
    """Preview review records without changing the graph or verifying their truth.

    Only explicitly identified OFFERS edges are accepted. A recorded review is
    structurally valid, not proof of reviewer authority or benefit applicability.
    """
    if not isinstance(edges, list) or not isinstance(reviews, list):
        raise ValueError('edges and reviews must be arrays')
    by_id = {}
    for edge in edges:
        if not isinstance(edge, dict) or edge.get('type') != 'OFFERS':
            raise ValueError('each edge must be an OFFERS object')
        edge_id = _identifier(edge.get('id'))
        source, target = _identifier(edge.get('source')), _identifier(edge.get('target'))
        if not edge_id or not source or not target or edge_id in by_id:
            raise ValueError('edge identifiers and endpoints must be present and unique')
        by_id[edge_id] = edge
    reviewed = {}
    for review in reviews:
        if not isinstance(review, dict):
            raise ValueError('review must be an object')
        edge_id = _identifier(review.get('edge_id'))
        edge = by_id.get(edge_id)
        if not edge or edge_id in reviewed or review.get('source') != edge['source'] or review.get('target') != edge['target']:
            raise ValueError('review must match one unique edge and its endpoints')
        if review.get('decision') not in {'supported', 'not_supported', 'uncertain'}:
            raise ValueError('invalid review decision')
        if not isinstance(review.get('reviewer'), str) or not review['reviewer'].strip():
            raise ValueError('reviewer is required')
        if not isinstance(review.get('doc_sha256'), str) or not re.fullmatch(r'[0-9a-fA-F]{64}', review['doc_sha256']):
            raise ValueError('document hash is required')
        if type(review.get('page_no')) is not int or review['page_no'] < 1:
            raise ValueError('page must be a positive integer')
        try:
            when = datetime.fromisoformat(review.get('reviewed_at'))
            if when.utcoffset() is None:
                raise ValueError('timezone required')
        except (TypeError, ValueError):
            raise ValueError('review time must include a timezone') from None
        reviewed[edge_id] = review['decision']
    return [
        {'edge_id': edge_id, 'status': 'review_recorded' if edge_id in reviewed else
         'candidate' if edge.get('origin') == 'document_index' else 'unknown',
         'decision': reviewed.get(edge_id)}
        for edge_id, edge in by_id.items()
    ]


def audit_graph(graph: dict) -> dict:
    """Check provided edge identifiers; missing identifiers limit conclusions.

    ``id`` and ``_fp_id`` are aliases for the same edge. Node evidence is
    counted but node referential integrity is outside this check's scope.
    """
    if not isinstance(graph, dict):
        raise ValueError('input must be a JSON object')
    edges, evidence = graph.get('edges'), graph.get('evidence')
    if not isinstance(edges, list) or not isinstance(evidence, list):
        raise ValueError('edges and evidence must both be arrays')
    if any(not isinstance(row, dict) for row in edges + evidence):
        raise ValueError('each edge and evidence item must be an object')
    unresolved_evidence = graph.get('unresolved_edge_evidence', [])
    if not isinstance(unresolved_evidence, list) or any(not isinstance(row, dict) for row in unresolved_evidence):
        raise ValueError('unresolved_edge_evidence must be an array of objects')

    counts: Counter[str] = Counter()
    unidentified = 0
    for edge in edges:
        aliases = {_identifier(edge.get('id')), _identifier(edge.get('_fp_id'))} - {None}
        if not aliases:
            unidentified += 1
        counts.update(aliases)
    duplicates = sorted(key for key, count in counts.items() if count > 1)
    unknown_refs: set[str] = set()
    unbound = node_count = ambiguous = 0
    for row in evidence:
        edge_id, node_id = _identifier(row.get('edge_id')), _identifier(row.get('node_id'))
        if edge_id and node_id:
            ambiguous += 1
        elif edge_id:
            if edge_id not in counts:
                unknown_refs.add(edge_id)
        elif node_id:
            node_count += 1
        else:
            unbound += 1
    dangling = sorted(unknown_refs) if unidentified == 0 else []
    unresolved = sorted(unknown_refs) if unidentified else []
    status = 'findings' if duplicates or dangling or unbound or ambiguous or unresolved_evidence else 'incomplete' if unidentified else 'ok'
    return {
        'status': status, 'edge_count': len(edges), 'evidence_count': len(evidence),
        'node_evidence_count': node_count, 'unidentified_edge_count': unidentified,
        'unresolved_edge_evidence_count': len(unresolved_evidence),
        'unbound_evidence_count': unbound, 'ambiguous_evidence_count': ambiguous,
        'duplicate_edge_ids': duplicates, 'dangling_edge_ids': dangling,
        'unresolved_edge_ids': unresolved,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Check edge references in a local graph JSON file.')
    parser.add_argument('input', type=Path, help='graph JSON, or evidence CSV with --source-refs-csv')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--source-refs', action='store_true', help='group evidence locations from graph JSON')
    mode.add_argument('--source-refs-csv', action='store_true', help='group locations from an evidence CSV')
    args = parser.parse_args(argv)
    try:
        if args.source_refs_csv:
            with args.input.open(encoding='utf-8-sig', newline='') as stream:
                reader = csv.DictReader(stream)
                required = {'node_id', 'edge_id', 'doc_sha256', 'page_no', 'start_pos', 'end_pos', 'quote_status'}
                if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)) or not required <= set(reader.fieldnames):
                    raise ValueError('evidence CSV is missing required columns or has duplicate columns')
                rows = list(reader)
                if any(None in row for row in rows):
                    raise ValueError('evidence CSV contains extra values')
            report = group_source_refs(rows)
            report['status'] = 'incomplete' if report['unresolved'] or not report['groups'] else 'ok'
        else:
            with args.input.open(encoding='utf-8') as stream:
                graph = json.load(stream)
        if args.source_refs:
            if not isinstance(graph, dict):
                raise ValueError('input must be a JSON object')
            report = group_source_refs(graph.get('evidence'))
            report['status'] = 'incomplete' if report['unresolved'] or not report['groups'] else 'ok'
        elif not args.source_refs_csv:
            report = audit_graph(graph)
    except (OSError, UnicodeError, json.JSONDecodeError, csv.Error, ValueError) as exc:
        parser.exit(2, f'Input error: {exc}\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return {'ok': 0, 'findings': 1, 'incomplete': 2}[report['status']]


if __name__ == '__main__':
    raise SystemExit(main())
