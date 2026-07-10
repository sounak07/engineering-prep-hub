## Candidate Prompt

# We run a shared dev environment plus multiple developer sandboxes.

# An external system sends callback requests to a single shared URL. When a callback arrives, we want to forward it to:

# 1. the matching handler in the shared environment
# 2. the same handler in any sandbox where that handler is deployed

# Your task is to implement a function that builds the list of internal URLs to forward the request to.

# ```
# buildForwardingUrls(input) -> result
# ```

# You do not need to make HTTP requests. Just return the URLs.

## Example Input

# ```json
# {
#   "requestPath": "/payments/provider-a/events/settled?event=evt_123",
#   "routes": [
#     {
#       "prefix": "/payments/provider-a/",
#       "handler": "payments-provider-a-callback",
#       "upstreamPath": "/callback/"
#     },
#     {
#       "prefix": "/payments/",
#       "handler": "payments-api",
#       "upstreamPath": "/"
#     },
#     
#   ],
#   "sandboxes": [
#     {
#       "name": "sandbox-101",
#       "handlers": ["payments-provider-a-callback"]
#     },
#     {
#       "name": "sandbox-102",
#       "handlers": ["cards-provider-b-callback"]
#     }
#   ],
#   "sharedEnvironment": "shared-dev",
#   "internalDomain": "internal",
#   "fanoutLimit": 10
# }
# ```

## Expected Output

# ```json
# {
#   "status": "MATCHED",
#   "urls": [
#     "http://payments-provider-a-callback.shared-dev.internal/callback/events/settled?event=evt_123",
#     "http://payments-provider-a-callback.sandbox-101.internal/callback/events/settled?event=evt_123"
#   ],
#   "warnings": []
# }
# ```

from pydantic import BaseModel
from urllib.parse import urlsplit


class Route(BaseModel):
    prefix: str
    handler: str
    upstreamPath: str


class Sandbox(BaseModel):
    name: str
    handlers: list[str]


class SharedEnvConfig(BaseModel):
    requestPath: str
    routes: list[Route]
    sandboxes: list[Sandbox]
    sharedEnvironment: str
    internalDomain: str
    fanoutLimit: int


class Response(BaseModel):
    status: str
    urls: list[str]
    warnings: list[str]


def buildForwardingUrls(config: SharedEnvConfig) -> Response:
    parsed = urlsplit(config.requestPath)

    request_path = parsed.path
    print('asa', request_path)
    query = parsed.query

    # --------------------------------------------------
    # Find all matching routes
    # --------------------------------------------------
    matching_routes = [
        route
        for route in config.routes
        if request_path.startswith(route.prefix)
    ]

    if not matching_routes:
        return Response(
            status="NO_MATCH",
            urls=[],
            warnings=[]
        )

    # --------------------------------------------------
    # Longest prefix wins
    # --------------------------------------------------
    selected_route = max(
        matching_routes,
        key=lambda route: len(route.prefix)
    )

    # --------------------------------------------------
    # Compute remaining path after prefix
    # --------------------------------------------------
    print('a', request_path, selected_route.prefix)
    suffix = request_path[len(selected_route.prefix):]
    print('b', suffix)

    upstream = selected_route.upstreamPath.rstrip("/")
    suffix = suffix.lstrip("/")


    final_path = upstream

    print('c', final_path)


    if suffix:
        final_path += "/" + suffix

    if query:
        final_path += f"?{query}"

    urls = []
    warnings = []

    # --------------------------------------------------
    # Shared environment
    # --------------------------------------------------
    urls.append(
        f"http://{selected_route.handler}."
        f"{config.sharedEnvironment}."
        f"{config.internalDomain}"
        f"{final_path}"
    )

    # --------------------------------------------------
    # Sandbox fanout
    # --------------------------------------------------
    for sandbox in config.sandboxes:
        if selected_route.handler not in sandbox.handlers:
            continue

        if len(urls) >= config.fanoutLimit:
            warnings.append(
                f"Fanout limit of {config.fanoutLimit} reached"
            )
            break

        urls.append(
            f"http://{selected_route.handler}."
            f"{sandbox.name}."
            f"{config.internalDomain}"
            f"{final_path}"
        )

    return Response(
        status="MATCHED",
        urls=urls,
        warnings=warnings
    )


buildForwardingUrls(
    SharedEnvConfig(
        requestPath="/payments/provider-a/events/settled?event=evt_123",
        routes=[
            Route(prefix="/payments/provider-a/", handler="payments-provider-a-callback", upstreamPath="/callback/"),
            Route(prefix="/payments/", handler="payments-api", upstreamPath="/"),
        ],
        sandboxes=[
            Sandbox(name="sandbox-101", handlers=["payments-provider-a-callback"]),
            Sandbox(name="sandbox-102", handlers=["cards-provider-b-callback"]),
        ],
        sharedEnvironment="shared-dev",
        internalDomain="internal",
        fanoutLimit=10,
    )
)
