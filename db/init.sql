-- db/init.sql
CREATE TABLE IF NOT EXISTS passengers (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS drivers (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rides (
    id SERIAL PRIMARY KEY,
    passenger_id INT NOT NULL REFERENCES passengers(id) ON DELETE CASCADE,
    driver_id INT REFERENCES drivers(id) ON DELETE SET NULL,
    status TEXT NOT NULL, -- pending, accepted, completed, cancelled
    requested_at TIMESTAMP DEFAULT NOW(),
    accepted_at TIMESTAMP,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS rides_updated_at ON rides;
CREATE TRIGGER rides_updated_at
BEFORE UPDATE ON rides
FOR EACH ROW
EXECUTE PROCEDURE update_updated_at_column();

-- Seed a few passengers and drivers if not exists
INSERT INTO passengers (name)
SELECT 'Alice' WHERE NOT EXISTS (SELECT 1 FROM passengers WHERE name = 'Alice');

INSERT INTO passengers (name)
SELECT 'Bob' WHERE NOT EXISTS (SELECT 1 FROM passengers WHERE name = 'Bob');

INSERT INTO drivers (name, available)
SELECT 'Driver1', TRUE WHERE NOT EXISTS (SELECT 1 FROM drivers WHERE name = 'Driver1');

INSERT INTO drivers (name, available)
SELECT 'Driver2', TRUE WHERE NOT EXISTS (SELECT 1 FROM drivers WHERE name = 'Driver2');
