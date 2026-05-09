use utoipa::openapi::security::{HttpAuthScheme, HttpBuilder, SecurityScheme};
use utoipa::Modify;
use utoipa::OpenApi;

#[derive(OpenApi)]
#[openapi(
    paths(
        crate::presentation::controllers::health_controller::health_check,
        crate::presentation::controllers::registration_controller::register,
        crate::presentation::controllers::registration_controller::verify,
        crate::presentation::controllers::registration_controller::resend_verification,
        crate::presentation::controllers::authentication_controller::login,
        crate::presentation::controllers::authentication_controller::logout,
        crate::presentation::controllers::authentication_controller::refresh_token,
        crate::presentation::controllers::authentication_controller::validate_token,
        crate::presentation::controllers::admin_controller::list_users,
        crate::presentation::controllers::admin_controller::get_user,
        crate::presentation::controllers::admin_controller::create_user,
        crate::presentation::controllers::admin_controller::update_user,
        crate::presentation::controllers::admin_controller::delete_user,
        crate::presentation::controllers::invitation_controller::create_invitation,
        crate::presentation::controllers::invitation_controller::list_invitations,
        crate::presentation::controllers::invitation_controller::get_invitation,
        crate::presentation::controllers::invitation_controller::accept_invitation,
        crate::presentation::controllers::invitation_controller::cancel_invitation,
    ),
    components(schemas(
        crate::application::dtos::health::HealthResponse,
        crate::application::dtos::registration::RegisterRequest,
        crate::application::dtos::registration::RegisterResponse,
        crate::application::dtos::registration::VerifyRequest,
        crate::application::dtos::registration::ResendRequest,
        crate::application::dtos::registration::MessageResponse,
        crate::application::dtos::authentication::LoginRequest,
        crate::application::dtos::authentication::LoginResponse,
        crate::application::dtos::authentication::LogoutRequest,
        crate::application::dtos::authentication::RefreshRequest,
        crate::application::dtos::authentication::ValidateRequest,
        crate::application::dtos::authentication::ValidateResponse,
        crate::application::dtos::admin::CreateUserRequest,
        crate::application::dtos::admin::UpdateUserRequest,
        crate::application::dtos::admin::UserResponse,
        crate::application::dtos::admin::MessageResponse,
        crate::application::dtos::invitation::CreateInvitationRequest,
        crate::application::dtos::invitation::InvitationResponse,
        crate::application::dtos::invitation::AcceptInvitationRequest,
        crate::application::dtos::invitation::MessageResponse,
    )),
    modifiers(&SecurityAddon),
    tags(
        (name = "Health", description = "Health check endpoints"),
        (name = "Registration", description = "User registration and verification"),
        (name = "Authentication", description = "Authentication endpoints"),
        (name = "Admin", description = "Admin user management"),
        (name = "Invitations", description = "Invitation management")
    ),
    info(
        title = "Auth Service API",
        version = "1.0.0",
        description = "Authentication and user management service"
    )
)]
pub struct ApiDoc;

struct SecurityAddon;

impl Modify for SecurityAddon {
    fn modify(&self, openapi: &mut utoipa::openapi::OpenApi) {
        // We get the components, or create them if they don't exist
        let components = openapi.components.as_mut().unwrap();

        components.add_security_scheme(
            "bearer_auth", // This MUST match the name in your controller path macros
            SecurityScheme::Http(
                HttpBuilder::new()
                    .scheme(HttpAuthScheme::Bearer)
                    .bearer_format("JWT")
                    .description(Some("Enter your Keycloak JWT token".to_string()))
                    .build(),
            ),
        );
    }
}
