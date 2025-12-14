-- CRM Database initialization
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    user_id VARCHAR(255) NOT NULL,
    prothesis_id VARCHAR(255) NOT NULL,
    order_date DATE NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS protheses (
    id SERIAL PRIMARY KEY,
    prothesis_id VARCHAR(255) UNIQUE NOT NULL,
    customer_id INTEGER REFERENCES customers(id),
    user_id VARCHAR(255) NOT NULL,
    model VARCHAR(100),
    serial_number VARCHAR(100),
    manufactured_date DATE,
    warranty_until DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO customers (user_id, email, first_name, last_name, phone) VALUES
('prothetic1', 'prothetic1@example.com', 'Prothetic', 'One', '+7-900-111-1111'),
('prothetic2', 'prothetic2@example.com', 'Prothetic', 'Two', '+7-900-222-2222'),
('prothetic3', 'prothetic3@example.com', 'Prothetic', 'Three', '+7-900-333-3333')
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO protheses (prothesis_id, customer_id, user_id, model, serial_number, manufactured_date, warranty_until) VALUES
('PROT-001', 1, 'prothetic1', 'BionicPRO-X1', 'SN-2024-001', '2024-01-15', '2027-01-15'),
('PROT-002', 2, 'prothetic2', 'BionicPRO-X1', 'SN-2024-002', '2024-02-20', '2027-02-20'),
('PROT-003', 3, 'prothetic3', 'BionicPRO-X2', 'SN-2024-003', '2024-03-10', '2027-03-10')
ON CONFLICT (prothesis_id) DO NOTHING;

INSERT INTO orders (customer_id, user_id, prothesis_id, order_date, status) VALUES
(1, 'prothetic1', 'PROT-001', '2024-01-10', 'active'),
(2, 'prothetic2', 'PROT-002', '2024-02-15', 'active'),
(3, 'prothetic3', 'PROT-003', '2024-03-05', 'active')
ON CONFLICT DO NOTHING;

