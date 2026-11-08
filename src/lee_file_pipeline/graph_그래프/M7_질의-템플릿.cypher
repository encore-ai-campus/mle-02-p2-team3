// M7 read-only templates for Neo4j Browser. Supply parameters; do not hardcode names.
// Run these only against the actual M6 import for $m6_run_id and verify returned rows.
// Query screenshots must omit source text, secrets, and sensitive connection details.

// Q1 — 카드 → 혜택, with optional condition, limit, and applicable/excluded target.
// Params: $m6_run_id, $card_id
MATCH (c:FpCard {id: $card_id})-[offers:FP_OFFERS]->(b:FpBenefit)
WHERE c.run_id = $m6_run_id
  AND offers.run_id = $m6_run_id
  AND b.run_id = $m6_run_id
OPTIONAL MATCH (b)-[conditionRel:FP_HAS_CONDITION]->(condition:FpCondition)
WHERE conditionRel.run_id = $m6_run_id
  AND condition.run_id = $m6_run_id
OPTIONAL MATCH (b)-[limitRel:FP_HAS_LIMIT]->(limit:FpLimit)
WHERE limitRel.run_id = $m6_run_id
  AND limit.run_id = $m6_run_id
OPTIONAL MATCH (b)-[appliesRel:FP_APPLIES_TO|FP_EXCLUDES]->(target:FpTarget)
WHERE appliesRel.run_id = $m6_run_id
  AND target.run_id = $m6_run_id
RETURN c.id AS card_id, c.name AS card_name,
       b.id AS benefit_id, b.name AS benefit_name,
       condition.id AS condition_id, condition.name AS condition,
       limit.id AS limit_id, limit.name AS limit,
       type(appliesRel) AS target_relation, target.id AS target_id, target.name AS target
ORDER BY benefit_name, condition_id, limit_id, target_relation, target_id;

// Q2 — target → benefit → card.
// Params: $m6_run_id, $target_id
MATCH (t:FpTarget {id: $target_id})<-[applies:FP_APPLIES_TO|FP_EXCLUDES]-(b:FpBenefit)
      <-[offers:FP_OFFERS]-(c:FpCard)
WHERE t.run_id = $m6_run_id
  AND applies.run_id = $m6_run_id
  AND b.run_id = $m6_run_id
  AND offers.run_id = $m6_run_id
  AND c.run_id = $m6_run_id
RETURN t.id AS target_id, t.name AS target, type(applies) AS target_relation,
       b.id AS benefit_id, b.name AS benefit,
       c.id AS card_id, c.name AS card
ORDER BY benefit, card;

// Q3a — evidence location attached to a node.
// Params: $m6_run_id, $node_id
MATCH (n)-[:FP_HAS_EVIDENCE]->(e:FpEvidence)
WHERE n.id = $node_id
  AND n.run_id = $m6_run_id
RETURN labels(n) AS node_labels, n.id AS node_id,
       e.doc_sha256 AS doc_sha256, e.page_no AS page_no,
       e.start_pos AS start_pos, e.end_pos AS end_pos,
       e.quote_status AS quote_status
ORDER BY doc_sha256, page_no, start_pos;

// Q3b — evidence location attached to a relationship (evidence stores edge_id).
// Params: $m6_run_id, $edge_id
MATCH (source)-[r]->(target), (e:FpEvidence {edge_id: $edge_id})
WHERE r.id = $edge_id
  AND r.run_id = $m6_run_id
  AND source.run_id = $m6_run_id
  AND target.run_id = $m6_run_id
RETURN type(r) AS relationship_type, r.id AS edge_id,
       e.doc_sha256 AS doc_sha256, e.page_no AS page_no,
       e.start_pos AS start_pos, e.end_pos AS end_pos,
       e.quote_status AS quote_status
ORDER BY doc_sha256, page_no, start_pos;
