use crate::core::errors::{AppError, AppResult};
use crate::domain::entities::UserReview;
use crate::domain::repositories::ReviewRepository;
use async_trait::async_trait;
use sqlx::PgPool;

pub struct PgReviewRepository {
    pool: PgPool,
}

impl PgReviewRepository {
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }
}

#[async_trait]
impl ReviewRepository for PgReviewRepository {
    async fn create(
        &self,
        review_id: String,
        user_id: String,
        station_id: String,
        rating: i32,
        review_text: Option<String>,
        created_by: String,
    ) -> AppResult<UserReview> {
        let review = sqlx::query_as::<_, UserReview>(
            r#"
            INSERT INTO user_reviews (review_id, user_id, station_id, rating, review_text, created_by, updated_by)
            VALUES ($1, $2, $3, $4, $5, $6, $6)
            RETURNING *
            "#,
        )
        .bind(&review_id)
        .bind(&user_id)
        .bind(&station_id)
        .bind(rating)
        .bind(&review_text)
        .bind(&created_by)
        .fetch_one(&self.pool)
        .await?;

        Ok(review)
    }

    async fn find_by_station(&self, station_id: &str) -> AppResult<Vec<UserReview>> {
        let reviews = sqlx::query_as::<_, UserReview>(
            r#"
            SELECT * FROM user_reviews
            WHERE station_id = $1
            ORDER BY created_at DESC
            "#,
        )
        .bind(station_id)
        .fetch_all(&self.pool)
        .await?;

        Ok(reviews)
    }

    async fn find_by_id(&self, review_id: &str) -> AppResult<Option<UserReview>> {
        let review = sqlx::query_as::<_, UserReview>(
            r#"
            SELECT * FROM user_reviews
            WHERE review_id = $1
            "#,
        )
        .bind(review_id)
        .fetch_optional(&self.pool)
        .await?;

        Ok(review)
    }

    async fn update(
        &self,
        review_id: &str,
        rating: Option<i32>,
        review_text: Option<String>,
        updated_by: String,
    ) -> AppResult<UserReview> {
        let existing = self.find_by_id(review_id).await?;
        if existing.is_none() {
            return Err(AppError::NotFound(format!(
                "Review with id {} not found",
                review_id
            )));
        }

        let review = sqlx::query_as::<_, UserReview>(
            r#"
            UPDATE user_reviews
            SET 
                rating = COALESCE($2, rating),
                review_text = COALESCE($3, review_text),
                updated_by = $4,
                updated_at = NOW()
            WHERE review_id = $1
            RETURNING *
            "#,
        )
        .bind(review_id)
        .bind(rating)
        .bind(&review_text)
        .bind(&updated_by)
        .fetch_one(&self.pool)
        .await?;

        Ok(review)
    }

    async fn delete(&self, review_id: &str) -> AppResult<()> {
        let result = sqlx::query(
            r#"
            DELETE FROM user_reviews
            WHERE review_id = $1
            "#,
        )
        .bind(review_id)
        .execute(&self.pool)
        .await?;

        if result.rows_affected() == 0 {
            return Err(AppError::NotFound(format!(
                "Review with id {} not found",
                review_id
            )));
        }

        Ok(())
    }
}
