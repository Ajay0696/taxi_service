-- passengers table
CREATE TABLE IF NOT EXISTS passengers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

-- drivers table
CREATE TABLE IF NOT EXISTS drivers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    available BOOLEAN DEFAULT TRUE
);

-- rides table
CREATE TABLE IF NOT EXISTS rides (
    id SERIAL PRIMARY KEY,
    passenger_id INTEGER NOT NULL REFERENCES passengers(id),
    driver_id INTEGER REFERENCES drivers(id),
    status VARCHAR(20) NOT NULL, -- 'pending', 'accepted', 'completed'
    requested_at TIMESTAMP DEFAULT NOW(),
    accepted_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Insert some sample passengers
INSERT INTO passengers (name) VALUES
('Alice'),
('Bob'),
('Charlie'),
('Diana'),
('Ethan'),
('Fiona'),
('George'),
('Hannah'),
('Ian'),
('Julia');

-- Insert some sample drivers
INSERT INTO drivers (name, available) VALUES
('Driver1', TRUE),
('Driver2', TRUE),
('Driver3', TRUE),
('Driver4', TRUE),
('Driver5', TRUE);
