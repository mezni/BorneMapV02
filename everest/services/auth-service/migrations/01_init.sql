-- Create enums
CREATE TYPE user_role AS ENUM ('user', 'admin', 'partner', 'operator');
CREATE TYPE user_status AS ENUM ('active', 'inactive', 'suspended', 'deleted');
CREATE TYPE source AS ENUM ('web', 'api', 'admin', 'invitation');
CREATE TYPE registration_status AS ENUM ('pending', 'active', 'verification_expired', 'cancelled');
CREATE TYPE invitation_status AS ENUM ('pending', 'accepted', 'expired', 'cancelled');

-- Users table
CREATE TABLE users (
    user_id VARCHAR(50) PRIMARY KEY,
    keycloak_id VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(20),
    role user_role NOT NULL DEFAULT 'user',
    status user_status NOT NULL DEFAULT 'active',
    source source NOT NULL DEFAULT 'web',
    network_id VARCHAR(50) NOT NULL DEFAULT 'X',
    station_id VARCHAR(50) NOT NULL DEFAULT 'X',
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- User registrations table
CREATE TABLE user_registrations (
    registration_id VARCHAR(50) PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    username VARCHAR(100) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(20),
    keycloak_id VARCHAR(100),
    verification_token VARCHAR(100) NOT NULL,
    status registration_status NOT NULL DEFAULT 'pending',
    source source NOT NULL DEFAULT 'web',
    ip_address VARCHAR(50),
    user_agent TEXT,
    resend_count INTEGER NOT NULL DEFAULT 0,
    expires_at TIMESTAMPTZ NOT NULL,
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Invitations table
CREATE TABLE invitations (
    invitation_id VARCHAR(50) PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    email VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'user',
    invited_by VARCHAR(50) NOT NULL,
    status invitation_status NOT NULL DEFAULT 'pending',
    metadata JSONB,
    expires_at TIMESTAMPTZ NOT NULL,
    accepted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_keycloak_id ON users(keycloak_id);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_network_id ON users(network_id);

CREATE INDEX idx_registrations_email ON user_registrations(email);
CREATE INDEX idx_registrations_token ON user_registrations(verification_token);
CREATE INDEX idx_registrations_status ON user_registrations(status);
CREATE INDEX idx_registrations_expires_at ON user_registrations(expires_at);

CREATE INDEX idx_invitations_code ON invitations(code);
CREATE INDEX idx_invitations_email ON invitations(email);
CREATE INDEX idx_invitations_status ON invitations(status);
CREATE INDEX idx_invitations_expires_at ON invitations(expires_at);

INSERT INTO users (
    user_id,
    keycloak_id,
    email,
    username,
    phone,
    role,
    network_id,
    station_id,
    source
) VALUES (
    'USR-cccccccccccccccc',
    'kc-123456',
    'system@example.com',
    'system',
    '+1234567890',
    'admin',
    'X',
    'X',
    'admin'
);