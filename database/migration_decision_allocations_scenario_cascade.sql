-- Allow terrain deletion when farmer decisions reference business scenarios.
-- Without ON DELETE CASCADE on scenario_id, DELETE FROM terrains fails with:
--   ForeignKeyViolation on decision_allocations_scenario_id_fkey

ALTER TABLE decision_allocations
    DROP CONSTRAINT IF EXISTS decision_allocations_scenario_id_fkey;

ALTER TABLE decision_allocations
    ADD CONSTRAINT decision_allocations_scenario_id_fkey
    FOREIGN KEY (scenario_id)
    REFERENCES business_scenarios(id)
    ON DELETE CASCADE;
