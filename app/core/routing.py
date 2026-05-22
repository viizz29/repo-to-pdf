import json
from urllib.parse import parse_qsl, urlencode

from fastapi import Request
from fastapi.routing import APIRoute

from .hashids import decode_ids_in_payload


class HashIdRoute(APIRoute):
    def get_route_handler(self):
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request):
            if request.scope.get("path_params"):
                request.scope["path_params"] = decode_ids_in_payload(
                    request.scope["path_params"]
                )

            if request.scope.get("query_string"):
                query_pairs = parse_qsl(
                    request.scope["query_string"].decode("utf-8"),
                    keep_blank_values=True,
                )
                decoded_pairs = [
                    (key, decode_ids_in_payload({key: value})[key])
                    for key, value in query_pairs
                ]
                request.scope["query_string"] = urlencode(
                    decoded_pairs,
                    doseq=True,
                ).encode("utf-8")

            content_type = request.headers.get("content-type", "")
            if content_type.startswith("application/json"):
                body = await request.body()
                if body:
                    decoded_body = decode_ids_in_payload(json.loads(body))
                    updated_body = json.dumps(decoded_body).encode("utf-8")
                    request._body = updated_body

                    async def receive():
                        return {
                            "type": "http.request",
                            "body": updated_body,
                            "more_body": False,
                        }

                    request._receive = receive

            return await original_route_handler(request)

        return custom_route_handler
