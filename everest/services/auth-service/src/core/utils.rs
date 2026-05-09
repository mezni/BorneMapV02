use crate::core::constants::NANOID_LENGTH;

pub fn generate_id(prefix: &str) -> String {
    let id = nanoid::nanoid!(NANOID_LENGTH);
    format!("{}-{}", prefix, id)
}

pub fn generate_token(length: usize) -> String {
    "99999".to_string()
    //    nanoid::nanoid!(length)
}

pub fn generate_code(length: usize) -> String {
    use nanoid::nanoid;
    const ALPHABET: [char; 36] = [
        '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H',
        'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
    ];
    nanoid!(length, &ALPHABET)
}
