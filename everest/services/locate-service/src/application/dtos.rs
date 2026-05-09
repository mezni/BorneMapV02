use crate::domain::entities::{Station, UserReview};
use serde::{Deserialize, Serialize};
use utoipa::ToSchema;
use validator::Validate;

#[derive(Debug, Deserialize, ToSchema)]
pub struct NearbyStationsQuery {
    pub latitude: f64,
    pub longitude: f64,
    pub radius_meters: Option<i32>,
    pub limit: Option<i32>,
}

#[derive(Debug, Serialize, ToSchema)]
pub struct StationResponse {
    pub station_id: String,
    pub name: String,
    pub address: Option<String>,
    pub distance_meters: Option<f64>,
    pub has_available_connectors: Option<bool>,
    pub total_available_connectors: Option<i64>,
    pub max_power_kw: Option<f64>,
    pub power_tier: Option<String>,
    pub operator: Option<String>,
    pub latitude: Option<f64>,
    pub longitude: Option<f64>,
}

impl From<Station> for StationResponse {
    fn from(station: Station) -> Self {
        Self {
            station_id: station.station_id,
            name: station.name,
            address: station.address,
            distance_meters: station.distance_meters,
            has_available_connectors: station.has_available_connectors,
            total_available_connectors: station.total_available_connectors,
            max_power_kw: station.max_power_kw,
            power_tier: station.power_tier,
            operator: station.operator,
            latitude: station.latitude,
            longitude: station.longitude,
        }
    }
}

#[derive(Debug, Deserialize, Validate, ToSchema)]
pub struct CreateReviewRequest {
    pub station_id: String,
    #[validate(range(min = 1, max = 5))]
    pub rating: i32,
    pub review_text: Option<String>,
}

#[derive(Debug, Deserialize, ToSchema)]
pub struct UpdateReviewRequest {
    pub rating: Option<i32>,
    pub review_text: Option<String>,
}

#[derive(Debug, Serialize, ToSchema)]
pub struct ReviewResponse {
    pub review_id: String,
    pub user_id: String,
    pub station_id: String,
    pub rating: i32,
    pub review_text: Option<String>,
    pub created_at: String,
    pub updated_at: String,
}

impl From<UserReview> for ReviewResponse {
    fn from(review: UserReview) -> Self {
        Self {
            review_id: review.review_id,
            user_id: review.user_id,
            station_id: review.station_id,
            rating: review.rating,
            review_text: review.review_text,
            created_at: review.created_at.to_rfc3339(),
            updated_at: review.updated_at.to_rfc3339(),
        }
    }
}