use super::entities::{Station, UserReview};
use crate::core::errors::AppResult;
use async_trait::async_trait;

#[async_trait]
pub trait StationService: Send + Sync {
    async fn find_nearby_stations(
        &self,
        latitude: f64,
        longitude: f64,
        radius_meters: Option<i32>,
        limit: Option<i32>,
    ) -> AppResult<Vec<Station>>;
}

#[async_trait]
pub trait ReviewService: Send + Sync {
    async fn create_review(
        &self,
        user_id: String,
        station_id: String,
        rating: i32,
        review_text: Option<String>,
        created_by: String,
    ) -> AppResult<UserReview>;

    async fn get_reviews_by_station(&self, station_id: &str) -> AppResult<Vec<UserReview>>;

    async fn update_review(
        &self,
        review_id: &str,
        rating: Option<i32>,
        review_text: Option<String>,
        updated_by: String,
    ) -> AppResult<UserReview>;

    async fn delete_review(&self, review_id: &str) -> AppResult<()>;
}
