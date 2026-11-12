from authlib.integrations.starlette_client import OAuth
from app.config import settings

oauth = OAuth()

# -------------------- GOOGLE --------------------
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
    redirect_uri=settings.google_redirect_uri,
)

# -------------------- GITHUB --------------------
oauth.register(
    name="github",
    client_id=settings.github_client_id,
    client_secret=settings.github_client_secret,
    authorize_url="https://github.com/login/oauth/authorize",
    access_token_url="https://github.com/login/oauth/access_token",
    api_base_url="https://api.github.com/",
    client_kwargs={
        "scope": "read:user user:email repo" if settings.features.customer_accounts else "read:user repo",
        "token_endpoint_auth_method": "client_secret_post",
    },
    redirect_uri=settings.github_redirect_uri,
)

# -------------------- GITLAB --------------------
oauth.register(
    name="gitlab",
    client_id=settings.gitlab_client_id,
    client_secret=settings.gitlab_client_secret,
    authorize_url="https://gitlab.com/oauth/authorize",
    access_token_url="https://gitlab.com/oauth/token",
    api_base_url="https://gitlab.com/api/v4/",
    client_kwargs={
        "scope": "read_user read_repository",
        "token_endpoint_auth_method": "client_secret_post",
    },
    redirect_uri=settings.gitlab_redirect_uri,
)

# -------------------- BITBUCKET --------------------
oauth.register(
    name="bitbucket",
    client_id=settings.bitbucket_client_id,
    client_secret=settings.bitbucket_client_secret,
    authorize_url="https://bitbucket.org/site/oauth2/authorize",
    access_token_url="https://bitbucket.org/site/oauth2/access_token",
    api_base_url="https://api.bitbucket.org/2.0/",
    client_kwargs={
        "scope": "repository",
        "token_endpoint_auth_method": "client_secret_post",
    },
    redirect_uri=settings.bitbucket_redirect_uri,
)
