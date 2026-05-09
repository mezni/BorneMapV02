-- Create enums
CREATE TYPE user_role AS ENUM ('user', 'admin', 'partner', 'operator');
CREATE TYPE user_status AS ENUM ('active', 'inactive', 'suspended', 'deleted');
CREATE TYPE source AS ENUM ('web', 'api', 'admin', 'invitation');
CREATE TYPE registration_status AS ENUM ('pending', 'active', 'verification_expired', 'cancelled');
CREATE TYPE invitation_status AS ENUM ('pending', 'accepted', 'expired', 'cancelled');
