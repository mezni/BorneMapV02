use crate::core::constants::NANOID_LENGTH;

pub fn generate_id(prefix: &str) -> String {
    let id = nanoid::nanoid!(NANOID_LENGTH);
    format!("{}-{}", prefix, id)
}
