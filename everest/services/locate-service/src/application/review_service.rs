use crate::core::constants::*;
use crate::core::errors::{AppError, AppResult};
use crate::core::utils::generate_id;
use crate::domain::entities::UserReview;
use crate::domain::repositories::ReviewRepository;
use crate::domain::services::ReviewService;
use async_trait::async_trait;
use std::sync::Arc;

pub struct ReviewServiceImpl {
    review_repo: Arc<dyn ReviewRepository>,
}

impl ReviewServiceImpl {
    pub fn new(review_repo: Arc<dyn ReviewRepository>) -> Self {
        Self { review_repo }
    }
}

#[async_trait]
impl ReviewService for ReviewServiceImpl {
    async fn create_review(
        &self,
        user_id: String,
        station_id: String,
        rating: i32,
        review_text: Option<String>,
        created_by: String,
    ) -> AppResult<UserReview> {
        if rating < 1 || rating > 5 {
            return Err(AppError::ValidationError(
                "Rating must be between 1 and 5".to_string(),
            ));
        }

        let review_id = generate_id(REVIEW_ID_PREFIX);

        self.review_repo
            .create(
                review_id,
                user_id,
                station_id,
                rating,
                review_text,
                created_by,
            )
            .await
    }

    async fn get_reviews_by_station(&self, station_id: &str) -> AppResult<Vec<UserReview>> {
        self.review_repo.find_by_station(station_id).await
    }

    async fn update_review(
        &self,
        review_id: &str,
        rating: Option<i32>,
        review_text: Option<String>,
        updated_by: String,
    ) -> AppResult<UserReview> {
        if let Some(r) = rating {
            if r < 1 || r > 5 {
                return Err(AppError::ValidationError(
                    "Rating must be between 1 and 5".to_string(),
                ));
            }
        }

        self.review_repo
            .update(review_id, rating, review_text, updated_by)
            .await
    }

    async fn delete_review(&self, review_id: &str) -> AppResult<()> {
        self.review_repo.delete(review_id).await
    }
}
