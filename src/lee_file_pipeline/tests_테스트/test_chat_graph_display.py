from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import types

from payment_card.file_pipeline.chat.ui import ui_v2
from payment_card.file_pipeline.chat.ui.ui_v2 import graph_for_display


def test_display_translates_all_known_relations_without_mutating_input():
    translations = {'OFFERS': '제공', 'HAS_CONDITION': '조건', 'HAS_LIMIT': '한도',
                    'APPLIES_TO': '적용 대상', 'EXCLUDES': '제외 대상',
                    'MUTUALLY_EXCLUSIVE': '상호 배타', 'SUPPORTED_BY': '문서 근거'}
    graph = {'nodes': [{'id': 'a', 'label': 'Card', 'props': {'x': [1]}}],
             'edges': [{'source': 'a', 'target': 'b', 'type': key} for key in translations] +
                      [{'source': 'a', 'target': 'c', 'type': 'CUSTOM'}], 'seeds': ['a']}
    original = deepcopy(graph)
    shown = graph_for_display(graph)
    assert [edge['type'] for edge in shown['edges']] == [*translations.values(), 'CUSTOM']
    assert graph == original
    assert [(e['source'], e['target']) for e in shown['edges']] == [(e['source'], e['target']) for e in original['edges']]
    assert shown['nodes'] == original['nodes'] and shown['seeds'] == original['seeds']
    shown['nodes'][0]['props']['x'].append(2)
    assert graph == original


def test_document_fp_id_matches_evidence_without_inventing_pages():
    digest = 'a' * 64
    graph = {'nodes': [{'id': 'hashed-uuid', 'label': 'Document', 'name': '문서 aaaaaaaa',
                        'props': {'fp_id': 'doc:' + digest, 'summary': '쪽 99'}}], 'edges': []}
    without_refs = ui_v2.collect_sources(graph)
    with_refs = ui_v2.collect_sources(graph, [{'doc_sha256': digest, 'page_no': 3}])
    assert without_refs[0]['title'] == '문서 aaaaaaaa'
    assert without_refs[0]['pages'] == ui_v2.MISSING
    assert with_refs[0]['pages'] == [3]


def test_synthetic_document_groups_display_same_page_without_inventing_other_pages():
    from lee_file_pipeline.evidence_audit import group_source_refs

    first, second, unknown = 'a' * 64, 'b' * 64, 'c' * 64
    graph = {'nodes': [
        {'id': 'benefit', 'label': 'Benefit', 'name': '합성 혜택',
         'props': {'source_text': '합성 근거', 'source_text_pages': '2'}},
        *[{'id': f'doc-{digest[0]}', 'label': 'Document', 'props': {'fp_id': 'doc:' + digest}}
          for digest in (first, second, unknown)],
    ], 'edges': []}
    rows = [{'node_id': 'benefit', 'doc_sha256': digest, 'page_no': 2,
             'start_pos': 1, 'end_pos': 3, 'quote_status': 'located'} for digest in (first, second)]
    grouped = group_source_refs(rows)
    sources = ui_v2.collect_sources(graph, grouped['groups'])
    assert [(source['title'], source['pages']) for source in sources[1:4]] == [
        ('문서 aaaaaaaa', [2]), ('문서 bbbbbbbb', [2]), ('문서 cccccccc', ui_v2.MISSING)]
    assert sources[0]['text'] == '합성 근거'
    assert 'doc_sha256' not in sources[0]


def test_two_cards_with_same_benefit_name_keep_their_conditions_separate():
    graph = {'nodes': [
        {'id':'c1','label':'Card','name':'카드 A','props':{}},
        {'id':'c2','label':'Card','name':'카드 B','props':{}},
        {'id':'b1','label':'Benefit','name':'합성 혜택','props':{}},
        {'id':'b2','label':'Benefit','name':'합성 혜택','props':{}},
        {'id':'l1','label':'Limit','name':'한도 A','props':{'text':'합성 한도 A'}},
        {'id':'l2','label':'Limit','name':'한도 B','props':{'text':'합성 한도 B'}},
    ], 'edges': [
        {'source':'c1','target':'b1','type':'OFFERS'}, {'source':'c2','target':'b2','type':'OFFERS'},
        {'source':'b1','target':'l1','type':'HAS_LIMIT'}, {'source':'b2','target':'l2','type':'HAS_LIMIT'},
    ], 'seeds':['c1','c2']}
    rows = ui_v2.build_compare_table(graph)['rows']
    assert [row['한도'] for row in rows] == ['합성 한도 A', '합성 한도 B']


def test_user_screen_passes_only_display_copy_to_graph_renderer(monkeypatch):
    fake_rag = types.ModuleType('rag')
    fake_ui = types.ModuleType('ui')
    fake_ui.ui_v2 = ui_v2
    captured = {}
    fake_graph = types.ModuleType('graph_view')
    def build_html(data):
        captured['graph'] = json.loads(data)
        return '<html>synthetic</html>'
    fake_graph.build_html = build_html
    monkeypatch.setitem(sys.modules, 'rag', fake_rag)
    monkeypatch.setitem(sys.modules, 'ui', fake_ui)
    monkeypatch.setitem(sys.modules, 'graph_view', fake_graph)
    repo = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location('synthetic_app_v2', repo / 'src/card_benefit/payment_card/file_pipeline/chat/ui/app_v2.py')
    app = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app)
    monkeypatch.setattr(app.st, 'iframe', lambda html, height: captured.update(html=html), raising=False)
    graph = {'nodes': [], 'edges': [{'source': 'a', 'target': 'b', 'type': 'OFFERS'}], 'seeds': []}
    original = deepcopy(graph)
    app._render_graph(graph)
    assert captured['graph']['edges'][0]['type'] == '제공'
    assert graph == original


def test_synthetic_retrieval_to_sources_and_graph_without_live_db(monkeypatch):
    import pytest

    ids = ['00000000-0000-0000-0000-00000000000' + str(i) for i in range(1, 6)]
    digest = 'a' * 64
    rows = [
        {'id': ids[0], 'name': '합성 카드', 'label': 'Card', 'props': {}},
        {'id': ids[1], 'name': '합성 혜택', 'label': 'Benefit', 'props': {'source_text': '합성 근거', 'source_text_pages': '2'}},
        {'id': ids[2], 'name': '합성 조건', 'label': 'Condition', 'props': {}},
        {'id': ids[3], 'name': '합성 한도', 'label': 'Limit', 'props': {}},
        {'id': ids[4], 'name': '문서 aaaaaaaa', 'label': 'Document', 'props': {'fp_id': 'doc:' + digest}},
    ]
    edges = [
        {'source': ids[0], 'target': ids[1], 'type': 'OFFERS'},
        {'source': ids[1], 'target': ids[2], 'type': 'HAS_CONDITION'},
        {'source': ids[1], 'target': ids[3], 'type': 'HAS_LIMIT'},
        {'source': ids[1], 'target': ids[4], 'type': 'SUPPORTED_BY'},
    ]
    fake_db = types.ModuleType('db')
    fake_db.NODES = 'fake.nodes'
    fake_db.EDGES = 'fake.edges'
    calls = []
    def run_query(query, params):
        calls.append(query)
        if query.lstrip().lower().startswith('with recursive'):
            return rows
        if 'select id::text as id' in query:
            return rows[:1]
        if 'select source::text' in query:
            return edges
        raise AssertionError('unexpected query')
    fake_db.run_query = run_query
    monkeypatch.setitem(sys.modules, 'db', fake_db)
    monkeypatch.setitem(sys.modules, 'llm', types.ModuleType('llm'))
    monkeypatch.setitem(sys.modules, 'timing', types.ModuleType('timing'))
    repo = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location('synthetic_rag_for_source_test', repo / 'src/graphrag_chatbot/rag.py')
    rag = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, rag)
    spec.loader.exec_module(rag)
    graph = rag._explore(rag.Analysis(entities=['합성 카드'], hops=2))
    assert graph['seeds'] == [ids[0]] and len(graph['nodes']) == 5 and len(graph['edges']) == 4
    sources = ui_v2.collect_sources(graph)
    assert sources[0]['pages'] == [2] and sources[1]['title'] == '문서 aaaaaaaa'
    assert sources[1]['pages'] == ui_v2.MISSING  # No exact document evidence was supplied.
    assert [e['type'] for e in ui_v2.graph_for_display(graph)['edges']] == ['제공', '조건', '한도', '문서 근거']
    assert graph['edges'][0]['type'] == 'OFFERS'
    assert len(calls) == 3
    calls.clear()
    assert rag._explore(rag.Analysis(entities=[])) == {'nodes': [], 'edges': [], 'seeds': []}
    assert not calls
    def failed_query(query, params):
        raise RuntimeError('synthetic query failure')
    fake_db.run_query = failed_query
    with pytest.raises(RuntimeError, match='synthetic query failure'):
        rag._explore(rag.Analysis(entities=['합성 카드']))


def test_graph_html_contains_translated_edge_caption():
    repo = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location('synthetic_graph_view', repo / 'src/graphrag_chatbot/graph_view.py')
    view = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(view)
    graph = {'nodes': [
        {'id':'a','name':'합성 카드','label':'Card','props':{}},
        {'id':'b','name':'합성 혜택','label':'Benefit','props':{}},
    ], 'edges':[{'source':'a','target':'b','type':'OFFERS'}], 'seeds':['a']}
    html = view.build_html(json.dumps(ui_v2.graph_for_display(graph), ensure_ascii=False, sort_keys=True))
    assert '제공' in html or '\\uc81c\\uacf5' in html.lower()
    assert graph['edges'][0]['type'] == 'OFFERS'


def test_chat_ui_shows_error_when_retrieval_fails(monkeypatch):
    from streamlit.testing.v1 import AppTest
    fake_rag = types.ModuleType('rag')
    def fail_entities(*_args):
        raise RuntimeError('synthetic failure')
    fake_rag.list_entities = fail_entities
    monkeypatch.setitem(sys.modules, 'rag', fake_rag)
    repo = Path(__file__).resolve().parents[3]
    app = AppTest.from_file(str(repo / 'src/card_benefit/payment_card/file_pipeline/chat/ui/app_v2.py')).run()
    next(button for button in app.button if button.label.startswith('신세계 by JADE')).click().run()
    assert any('처리 중 오류가 발생했습니다' in str(element.value) for element in app.error)


def test_no_sources_has_explicit_missing_message():
    sources = ui_v2.collect_sources({'nodes': [], 'edges': [], 'seeds': []})
    assert sources[0]['title'] == ui_v2.MISSING
    assert sources[0]['pages'] == ui_v2.MISSING
    assert any(row['title'] == '안내' for row in sources)


def test_chat_ui_requests_clarification_when_no_entity_was_selected(monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.delenv('FP_QA_LOG', raising=False)
    fake_rag = types.ModuleType('rag')
    fake_rag.list_entities = lambda *_args: []
    fake_rag.analyze = lambda question, entities: types.SimpleNamespace(entities=[], intent='', hops=1)
    downstream_calls = []
    fake_rag.explore = lambda analysis: downstream_calls.append('explore')
    fake_rag.generate_stream = lambda question, graph, history: downstream_calls.append('answer')
    fake_llm = types.ModuleType('llm')
    fake_llm.usage_totals = lambda: {'prompt_tokens': 0, 'completion_tokens': 0, 'cost_usd': 0}
    monkeypatch.setitem(sys.modules, 'rag', fake_rag)
    monkeypatch.setitem(sys.modules, 'llm', fake_llm)
    repo = Path(__file__).resolve().parents[3]
    app = AppTest.from_file(str(repo / 'src/card_benefit/payment_card/file_pipeline/chat/ui/app_v2.py')).run()
    next(button for button in app.button if button.label.startswith('신세계 by JADE')).click().run()
    assert len(app.info) == 1
    assert '카드 상품' in str(app.info[0].value)
    assert not downstream_calls
    assert not app.error


def test_chat_ui_displays_document_pages_from_opt_in_evidence_query(monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.delenv('FP_QA_LOG', raising=False)
    monkeypatch.setenv('FP_SOURCE_EVIDENCE', '1')
    digest = 'a' * 64
    fake_rag = types.ModuleType('rag')
    fake_rag.list_entities = lambda *_args: []
    fake_rag.analyze = lambda *args: types.SimpleNamespace(entities=['합성 혜택'], intent='', hops=1)
    fake_rag.explore = lambda analysis: {'nodes': [
        {'id': 'uuid-b', 'label': 'Benefit', 'name': '합성 혜택', 'props': {'fp_id': 'fp-b'}},
        {'id': 'uuid-d', 'label': 'Document', 'props': {'fp_id': 'doc:' + digest}},
    ], 'edges': [], 'seeds': ['uuid-b']}
    fake_rag.generate_stream = lambda *args: iter(['합성 답변'])
    fake_llm = types.ModuleType('llm')
    fake_llm.usage_totals = lambda: {'prompt_tokens': 0, 'completion_tokens': 0, 'cost_usd': 0}
    fake_db = types.ModuleType('db')
    fake_db.run_query = lambda query, params: [
        {'node_id': 'fp-b', 'edge_id': None, 'doc_sha256': digest, 'page_no': 2,
         'start_pos': 1, 'end_pos': 3, 'quote_status': 'located'},
        {'node_id': 'fp-b', 'edge_id': None, 'doc_sha256': digest, 'page_no': 99,
         'start_pos': None, 'end_pos': None, 'quote_status': 'missing'}]
    monkeypatch.setitem(sys.modules, 'rag', fake_rag)
    monkeypatch.setitem(sys.modules, 'llm', fake_llm)
    monkeypatch.setitem(sys.modules, 'db', fake_db)
    repo = Path(__file__).resolve().parents[3]
    app = AppTest.from_file(str(repo / 'src/card_benefit/payment_card/file_pipeline/chat/ui/app_v2.py')).run()
    next(button for button in app.button if button.label.startswith('신세계 by JADE')).click().run()
    assert any('문서 aaaaaaaa' in str(element.value) and '쪽 2' in str(element.value) for element in app.markdown)
    assert not any('쪽 99' in str(element.value) for element in app.markdown)
    assert not app.exception
    def fail_query(*args):
        raise RuntimeError('synthetic database error')
    fake_db.run_query = fail_query
    failed_app = AppTest.from_file(str(repo / 'src/card_benefit/payment_card/file_pipeline/chat/ui/app_v2.py')).run()
    next(button for button in failed_app.button if button.label.startswith('신세계 by JADE')).click().run()
    assert any('문서별 근거 조회에 실패했습니다' in str(element.value) for element in failed_app.caption)
    assert not failed_app.exception


def test_display_evidence_distinguishes_disabled_failure_and_incomplete(monkeypatch):
    fake_ui = types.ModuleType('ui')
    fake_ui.ui_v2 = ui_v2
    monkeypatch.setitem(sys.modules, 'ui', fake_ui)
    monkeypatch.setitem(sys.modules, 'rag', types.ModuleType('rag'))
    db = types.ModuleType('db')
    calls = []
    def failed(query, params):
        calls.append(params)
        raise RuntimeError('synthetic failure')
    db.run_query = failed
    monkeypatch.setitem(sys.modules, 'db', db)
    repo = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location('synthetic_source_app', repo / 'src/card_benefit/payment_card/file_pipeline/chat/ui/app_v2.py')
    app = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app)
    graph = {'nodes': [{'label': 'Benefit', 'props': {'fp_id': 'fp-b'}}]}
    monkeypatch.delenv('FP_SOURCE_EVIDENCE', raising=False)
    assert app._display_evidence(graph) == ([], 'not_requested') and not calls
    monkeypatch.setenv('FP_SOURCE_EVIDENCE', '1')
    assert app._display_evidence({'nodes': []}) == ([], 'no_identifiers') and not calls
    assert app._display_evidence(graph) == ([], 'query_failed')
    db.run_query = lambda query, params: []
    assert app._display_evidence(graph) == ([], 'no_rows')
    db.run_query = lambda query, params: [{'node_id': 'fp-b'}] * 1001
    refs, status = app._display_evidence(graph)
    assert status == 'partial' and len(refs) == 1000
    db.run_query = lambda query, params: [{'node_id': 'fp-b'}]
    refs, status = app._display_evidence({'nodes': [*graph['nodes'], {'label': 'Benefit', 'props': {}}]})
    assert status == 'partial' and len(refs) == 1


def test_chat_ui_replaces_broad_refusal_with_graph_supported_benefit(monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.delenv('FP_QA_LOG', raising=False)
    monkeypatch.delenv('FP_SOURCE_EVIDENCE', raising=False)
    graph = {'nodes': [
        {'id': 'card', 'label': 'Card', 'name': '애터미 Any PLUS 카드', 'props': {'fp_id': 'fp-card'}},
        {'id': 'benefit', 'label': 'Benefit', 'name': '지역쇼핑/주유 하나머니 적립', 'props': {'fp_id': 'fp-benefit'}},
        {'id': 'limit', 'label': 'Limit', 'name': '주유 월 적립 한도 1만 하나머니', 'props': {}},
    ], 'edges': [
        {'source': 'card', 'target': 'benefit', 'type': 'OFFERS'},
        {'source': 'benefit', 'target': 'limit', 'type': 'HAS_LIMIT'},
    ], 'seeds': ['card', 'benefit', 'limit']}
    refusal = '애터미 Any PLUS 카드의 주유 혜택은 그래프에서 확인되지 않습니다.\n※ 확인되지 않은 항목: 주유 적립률·한도·조건'
    fake_rag = types.ModuleType('rag')
    fake_rag.list_entities = lambda *_args: []
    fake_rag.analyze = lambda *args: types.SimpleNamespace(entities=['애터미 Any PLUS 카드'], intent='주유 혜택', hops=1)
    fake_rag.explore = lambda analysis: graph
    fake_rag.generate_stream = lambda *args: iter([refusal])
    fake_llm = types.ModuleType('llm')
    fake_llm.usage_totals = lambda: {'prompt_tokens': 0, 'completion_tokens': 0, 'cost_usd': 0}
    monkeypatch.setitem(sys.modules, 'rag', fake_rag)
    monkeypatch.setitem(sys.modules, 'llm', fake_llm)

    repo = Path(__file__).resolve().parents[3]
    app = AppTest.from_file(str(repo / 'src/card_benefit/payment_card/file_pipeline/chat/ui/app_v2.py')).run()
    next(button for button in app.button if button.label.startswith('애터미 Any PLUS')).click().run()

    rendered = '\n'.join(str(element.value) for element in app.markdown)
    assert '그래프에서 애터미 Any PLUS 카드의' in rendered
    assert '지역쇼핑/주유 하나머니 적립' in rendered
    assert '주유 월 적립 한도 1만 하나머니' in rendered
    assert '주유 혜택은 그래프에서 확인되지 않습니다' not in rendered


def test_chat_ui_asks_for_card_when_analysis_has_no_entity(monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.delenv('FP_QA_LOG', raising=False)
    monkeypatch.setenv('FP_SOURCE_EVIDENCE', '1')
    question = '우리 카드의 연회비와 혜택을 알려줘.'
    entity_queries = []
    downstream_calls = []
    fake_rag = types.ModuleType('rag')
    fake_rag.list_entities = lambda query: entity_queries.append(query) or []
    fake_rag.analyze = lambda query, entities: types.SimpleNamespace(
        entities=[], intent='어떤 우리카드인지 확인한 뒤 조회', hops=1
    )
    fake_rag.explore = lambda *_args: downstream_calls.append('explore')
    fake_rag.generate_stream = lambda *_args: downstream_calls.append('answer')
    fake_llm = types.ModuleType('llm')
    fake_llm.usage_totals = lambda: {'prompt_tokens': 0, 'completion_tokens': 0, 'cost_usd': 0}
    fake_db = types.ModuleType('db')
    fake_db.run_query = lambda *_args, **_kwargs: downstream_calls.append('evidence')
    monkeypatch.setitem(sys.modules, 'rag', fake_rag)
    monkeypatch.setitem(sys.modules, 'llm', fake_llm)
    monkeypatch.setitem(sys.modules, 'db', fake_db)

    repo = Path(__file__).resolve().parents[3]
    app = AppTest.from_file(str(repo / 'src/card_benefit/payment_card/file_pipeline/chat/ui/app_v2.py')).run()
    app.session_state['v2_pending_question'] = question
    app.run()

    assert entity_queries == [question]
    assert not downstream_calls
    assert len(app.info) == 1
    assert '카드 상품' in str(app.info[0].value)
    assert not any('서비스나 팀 이름' in str(element.value) for element in app.markdown)
    assert not any('근거 조회 안내' in str(element.value) for element in app.markdown)
    current = app.session_state['v2_current']
    turn = app.session_state['v2_conversations'][current]['turns'][0]
    assert turn['clarification'] is True
