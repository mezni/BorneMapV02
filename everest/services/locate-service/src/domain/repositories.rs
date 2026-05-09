use super::entities::{Station, UserReview};
use crate::core::errors::AppResult;
use async_trait::async_trait;

#[async_trait]
pub trait StationRepository: Send + Sync {
    async fn find_nearby(
        &self,
        latitude: f64,
        longitude: f64,
        radius_meters: i32,
        limit: i32,
    ) -> AppResult<Vec<Station>>;
}

#[async_trait]
pub trait ReviewRepository: Send + Sync {
    async fn create(
        &self,
        review_id: String,
        user_id: String,
        station_id: String,
        rating: i32,
        review_text: Option<String>,
        created_by: String,
    ) -> AppResult<UserReview>;

    async fn find_by_station(&self, station_id: &str) -> AppResult<Vec<UserReview>>;
    async fn find_by_id(&self, review_id: &str) -> AppResult<Option<UserReview>>;

    async fn update(
        &self,
        review_id: &str,
        rating: Option<i32>,
        review_text: Option<String>,
        updated_by: String,
    ) -> AppResult<UserReview>;

    async fn delete(&self, review_id: &str) -> AppResult<()>;
}
