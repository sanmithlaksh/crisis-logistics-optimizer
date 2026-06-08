-- 1. Create Zones Table
CREATE TABLE IF NOT EXISTS zones (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    population INTEGER NOT NULL,
    severity TEXT CHECK (severity IN ('Critical', 'High', 'Medium', 'Low'))
);

-- 2. Create Resources Table
CREATE TABLE IF NOT EXISTS resources (
    resource_id SERIAL PRIMARY KEY,
    resource_name TEXT UNIQUE NOT NULL,
    available_quantity INTEGER NOT NULL,
    unit_weight DOUBLE PRECISION NOT NULL,
    utility_value INTEGER NOT NULL
);

-- 3. Create Requests Table
CREATE TABLE IF NOT EXISTS requests (
    request_id SERIAL PRIMARY KEY,
    zone_id INTEGER REFERENCES zones(id) ON DELETE CASCADE,
    resource_type TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    priority DOUBLE PRECISION NOT NULL,
    status TEXT CHECK (status IN ('Pending', 'Allocated', 'Partial', 'Delivered', 'Unfulfilled')) DEFAULT 'Pending',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Create Vehicles Table
CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    type TEXT NOT NULL,
    capacity_weight DOUBLE PRECISION NOT NULL,
    speed_kmh DOUBLE PRECISION NOT NULL,
    cost_per_km DOUBLE PRECISION NOT NULL,
    status TEXT CHECK (status IN ('Available', 'Dispatched', 'Maintenance')) DEFAULT 'Available'
);

-- 5. Create Roads Table
CREATE TABLE IF NOT EXISTS roads (
    road_id SERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    destination TEXT NOT NULL,
    distance_km DOUBLE PRECISION NOT NULL,
    risk_level TEXT CHECK (risk_level IN ('Normal', 'Flooded', 'Damaged', 'Blocked', 'Enemy-Controlled')) DEFAULT 'Normal'
);

-- Disable Row Level Security (RLS) for all tables to allow easy read/write via the client key for development.
ALTER TABLE zones DISABLE ROW LEVEL SECURITY;
ALTER TABLE resources DISABLE ROW LEVEL SECURITY;
ALTER TABLE requests DISABLE ROW LEVEL SECURITY;
ALTER TABLE vehicles DISABLE ROW LEVEL SECURITY;
ALTER TABLE roads DISABLE ROW LEVEL SECURITY;
