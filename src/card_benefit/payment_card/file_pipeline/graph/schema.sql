-- 검토용 초안. 실행하지 말 것: 팀의 DB/접두사/RLS 합의 전이다.
-- 모든 객체는 public의 pf_ 이름이며 RLS 정책을 만들지 않는다.

create table if not exists public.pf_load_runs (
  run_id text primary key,
  input_folder_name text not null,
  model_name text not null,
  started_at timestamptz not null,
  node_count integer not null default 0 check (node_count >= 0),
  edge_count integer not null default 0 check (edge_count >= 0),
  constraint pf_load_runs_id_nonempty check (length(run_id) > 0)
);

create table if not exists public.pf_nodes (
  id text primary key,
  node_type text not null check (node_type in ('Issuer', 'Card', 'Benefit', 'Condition', 'Limit', 'Target')),
  props jsonb not null default '{}'::jsonb,
  chunk_id text,
  run_id text not null references public.pf_load_runs(run_id),
  constraint pf_nodes_id_nonempty check (length(id) > 0),
  constraint pf_nodes_run_id_id_unique unique (run_id, id)
);

create table if not exists public.pf_edges (
  id text primary key,
  source_id text not null references public.pf_nodes(id),
  target_id text not null references public.pf_nodes(id),
  edge_type text not null check (edge_type in ('HAS_CONDITION', 'HAS_LIMIT', 'APPLIES_TO', 'EXCLUDES', 'MUTUALLY_EXCLUSIVE', 'OFFERS')),
  run_id text not null references public.pf_load_runs(run_id),
  constraint pf_edges_run_source_target_type_unique unique (run_id, source_id, target_id, edge_type),
  constraint pf_edges_run_id_id_unique unique (run_id, id),
  constraint pf_edges_no_self_mutual check (edge_type <> 'MUTUALLY_EXCLUSIVE' or source_id <> target_id)
);

create table if not exists public.pf_evidence (
  id bigint generated always as identity primary key,
  node_id text references public.pf_nodes(id),
  edge_id text references public.pf_edges(id),
  doc_sha256 text not null,
  page_no integer check (page_no >= 1),
  start_pos integer check (start_pos >= 1),
  end_pos integer check (end_pos >= start_pos),
  quote_status text not null check (quote_status in ('located', 'ambiguous', 'missing')),
  constraint pf_evidence_exactly_one_target check ((node_id is not null)::integer + (edge_id is not null)::integer = 1),
  constraint pf_evidence_sha256_shape check (doc_sha256 ~ '^[0-9a-fA-F]{64}$'),
  -- 위치를 못 찾은 인용문(missing)만 위치 열이 비어도 된다. located/ambiguous는 위치가 필수다.
  constraint pf_evidence_position_by_status check (
    (quote_status = 'missing') or (page_no is not null and start_pos is not null and end_pos is not null)
  )
);

create index if not exists pf_nodes_type_idx on public.pf_nodes (node_type);
create index if not exists pf_nodes_run_idx on public.pf_nodes (run_id);
create index if not exists pf_edges_source_idx on public.pf_edges (source_id);
create index if not exists pf_edges_target_idx on public.pf_edges (target_id);
create index if not exists pf_edges_type_idx on public.pf_edges (edge_type);
create index if not exists pf_edges_run_idx on public.pf_edges (run_id);
create index if not exists pf_evidence_node_idx on public.pf_evidence (node_id) where node_id is not null;
create index if not exists pf_evidence_edge_idx on public.pf_evidence (edge_id) where edge_id is not null;
create index if not exists pf_evidence_document_page_idx on public.pf_evidence (doc_sha256, page_no, start_pos, end_pos);

-- ALLOWED_RELATIONS 그대로 + 문서 인덱스의 상품 연결: Card -> Benefit (OFFERS).
-- 함수는 create or replace로 재실행해도 최신 정의로 갱신된다(pf_ 함수만 대상). 트리거는 IF NOT EXISTS 문법이 없어 중복 생성 예외로 조건부 처리한다.
  create or replace function public.pf_check_edge_endpoint_types()
  returns trigger
  language plpgsql
  set search_path = public
  as $pf_body$
  declare
    source_type text;
    target_type text;
    allowed boolean := false;
  begin
    select node_type into source_type from public.pf_nodes where id = new.source_id;
    select node_type into target_type from public.pf_nodes where id = new.target_id;
    if source_type is null or target_type is null then
      raise exception 'pf_edges endpoint is missing';
    end if;
    allowed := case new.edge_type
      when 'HAS_CONDITION' then source_type = 'Benefit' and target_type = 'Condition'
      when 'HAS_LIMIT' then source_type = 'Benefit' and target_type = 'Limit'
      when 'APPLIES_TO' then source_type = 'Benefit' and target_type = 'Target'
      when 'EXCLUDES' then source_type = 'Benefit' and target_type = 'Target'
      when 'MUTUALLY_EXCLUSIVE' then source_type = 'Benefit' and target_type = 'Benefit' and new.source_id <> new.target_id
      when 'OFFERS' then source_type = 'Card' and target_type = 'Benefit'
      else false
    end;
    if not allowed then
      raise exception 'pf_edges disallowed endpoint types for %: % -> %', new.edge_type, source_type, target_type;
    end if;
    return new;
  end
  $pf_body$;

do $pf_create_trigger$
begin
  begin
    create trigger pf_edges_endpoint_types_trg
      before insert or update of source_id, target_id, edge_type on public.pf_edges
      for each row execute function public.pf_check_edge_endpoint_types();
  exception when duplicate_object then
    null;
  end;
end
$pf_create_trigger$;

-- public는 Supabase API에 노출될 수 있다. 정책을 만들지 않아 기본 거부를 유지한다.
alter table public.pf_load_runs enable row level security;
alter table public.pf_nodes enable row level security;
alter table public.pf_edges enable row level security;
alter table public.pf_evidence enable row level security;
