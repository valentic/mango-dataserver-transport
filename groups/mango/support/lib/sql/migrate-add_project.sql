BEGIN;

-- Create the project table
CREATE TABLE project (
    id SERIAL PRIMARY KEY,
    name VARCHAR UNIQUE NOT NULL,
    label VARCHAR
);

-- Seed the initial projects
INSERT INTO project (name, label) VALUES
    ('conus', 'CONUS'),
    ('south_america', 'South America');

-- Add the project_id column and foreign key constraint to station
ALTER TABLE station
    ADD COLUMN project_id INTEGER REFERENCES project(id);

-- Backfill existing stations. Default to 'conus'
UPDATE station
    SET project_id = (SELECT id FROM project WHERE name = 'conus');

-- Enforce NOT NULL once all existing rows are populated
ALTER TABLE station
    ALTER COLUMN project_id SET NOT NULL;

COMMIT;

