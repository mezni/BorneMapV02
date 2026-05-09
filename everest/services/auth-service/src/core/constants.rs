// ID Prefixes
pub const USER_ID_PREFIX: &str = "USR";
pub const REGISTRATION_ID_PREFIX: &str = "REG";
pub const INVITATION_ID_PREFIX: &str = "INV";

// ID Length (without prefix)
pub const NANOID_LENGTH: usize = 16;

// Verification
pub const VERIFICATION_EXPIRY_HOURS: i64 = 24;
pub const MAX_RESEND_ATTEMPTS: i32 = 3;
pub const VERIFICATION_TOKEN_LENGTH: usize = 32;

// Invitations
pub const DEFAULT_INVITATION_EXPIRY_HOURS: i64 = 72;
pub const INVITATION_CODE_LENGTH: usize = 10;

// Default values
pub const DEFAULT_NETWORK_ID: &str = "X";
pub const DEFAULT_STATION_ID: &str = "X";

// Roles
pub const ROLE_USER: &str = "user";
pub const ROLE_ADMIN: &str = "admin";
pub const ROLE_PARTNER: &str = "partner";
pub const ROLE_OPERATOR: &str = "operator";
