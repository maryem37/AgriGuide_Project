-- Apply once on databases created before the detailed Business pipeline.
ALTER TABLE crop_recommendations
    ADD COLUMN IF NOT EXISTS cycle_jours SMALLINT;

ALTER TABLE business_scenarios
    ADD COLUMN IF NOT EXISTS superficie_max_financable_ha NUMERIC(10,2),
    ADD COLUMN IF NOT EXISTS superficie_conseillee_ha NUMERIC(10,2),
    ADD COLUMN IF NOT EXISTS scenario_payload JSONB;

UPDATE business_scenarios
SET scenario_payload = jsonb_build_object(
    'id', id,
    'terrain_id', terrain_id,
    'budget_input', budget_input,
    'culture', culture,
    'quantite_par_ha', quantite_par_ha,
    'profit_estime', profit_estime,
    'risque_score', risque_score,
    'risque_description', risque_description,
    'solution_risque', solution_risque,
    'matching_score', matching_score,
    'etude_marche', etude_marche,
    'created_at', created_at
)
WHERE scenario_payload IS NULL;

ALTER TABLE business_scenarios
    ALTER COLUMN scenario_payload SET NOT NULL;

ALTER TABLE farmer_decisions
    ADD COLUMN IF NOT EXISTS decision_payload JSONB;

ALTER TABLE decision_allocations
    ADD COLUMN IF NOT EXISTS cout_alloue NUMERIC(12,2);

CREATE INDEX IF NOT EXISTS idx_decisions_terrain_status
    ON farmer_decisions(terrain_id, statut, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_allocations_decision
    ON decision_allocations(decision_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_decision_scenario
    ON decision_allocations(decision_id, scenario_id);
