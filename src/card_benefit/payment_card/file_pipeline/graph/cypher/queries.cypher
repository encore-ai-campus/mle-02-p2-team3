// 1) Count nodes by Pf label.
MATCH (n:PfIssuer) RETURN 'PfIssuer' AS label, count(n) AS count
UNION ALL MATCH (n:PfCard) RETURN 'PfCard' AS label, count(n) AS count
UNION ALL MATCH (n:PfBenefit) RETURN 'PfBenefit' AS label, count(n) AS count
UNION ALL MATCH (n:PfCondition) RETURN 'PfCondition' AS label, count(n) AS count
UNION ALL MATCH (n:PfLimit) RETURN 'PfLimit' AS label, count(n) AS count
UNION ALL MATCH (n:PfTarget) RETURN 'PfTarget' AS label, count(n) AS count;

// 2) Find benefits offered by cards with a matching name.
MATCH (c:PfCard)-[:PF_OFFERS]->(b:PfBenefit)
WHERE toLower(coalesce(c.name, c.product_name, '')) CONTAINS '우리'
RETURN c.product_name AS card, b.name AS benefit, b.method AS method, b.rate AS rate
ORDER BY benefit LIMIT 30;

// 3) Explore benefit conditions, limits, and targets.
MATCH (c:PfCard)-[:PF_OFFERS]->(b:PfBenefit)
WHERE toLower(coalesce(c.name, c.product_name, '')) CONTAINS '우리'
OPTIONAL MATCH (b)-[:PF_HAS_CONDITION]->(condition:PfCondition)
OPTIONAL MATCH (b)-[:PF_HAS_LIMIT]->(limit:PfLimit)
OPTIONAL MATCH (b)-[:PF_APPLIES_TO]->(target:PfTarget)
RETURN c.product_name AS card, b.name AS benefit,
       collect(DISTINCT condition.text) AS conditions,
       collect(DISTINCT limit.text) AS limits,
       collect(DISTINCT target.text) AS targets
ORDER BY card, benefit LIMIT 30;

// 4) Find benefits that apply to coffee targets.
MATCH (b:PfBenefit)-[:PF_APPLIES_TO]->(t:PfTarget)
WHERE toLower(coalesce(t.name, t.text, '')) CONTAINS '커피'
RETURN b.name AS benefit, t.name AS target_name, t.text AS target_text
ORDER BY benefit LIMIT 30;

// 5) Find nodes with ambiguous evidence.
MATCH (n:PfIssuer|PfCard|PfBenefit|PfCondition|PfLimit|PfTarget)-[:PF_HAS_EVIDENCE]->(e:PfEvidence)
WHERE e.quote_status = 'ambiguous'
RETURN labels(n) AS labels, n.id AS node_id, e.doc_sha256 AS document,
       e.edge_id AS edge_id, e.quote_status AS status
ORDER BY document, node_id LIMIT 50;

// 6) Find mutually exclusive benefit pairs on the same card.
MATCH (c:PfCard)-[:PF_OFFERS]->(a:PfBenefit)-[:PF_MUTUALLY_EXCLUSIVE]-(b:PfBenefit)<-[:PF_OFFERS]-(c)
RETURN DISTINCT c.product_name AS card, a.name AS benefit_a, b.name AS benefit_b
ORDER BY card, benefit_a LIMIT 50;

// 7) Trace from a card to its benefit details.
MATCH path = (c:PfCard)-[:PF_OFFERS]->(b:PfBenefit)
             -[:PF_HAS_CONDITION|PF_HAS_LIMIT|PF_APPLIES_TO*0..1]->(detail:PfCondition|PfLimit|PfTarget)
RETURN path LIMIT 50;
