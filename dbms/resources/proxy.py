"""Image proxy resource — fetches external images server-side to bypass CORS."""

from urllib.request import Request, urlopen
from urllib.error import URLError

from flask import Response, request
from flask_restful import Resource
from werkzeug.exceptions import BadRequest, BadGateway


PROXY_TIMEOUT = 10


class ImageProxy(Resource):
    """Proxy for external images.

    Browsers block cross-origin <img> loads when the Flutter web engine
    adds ``crossorigin``.  This endpoint fetches the image server-side so
    the browser sees it as same-origin.
    """

    def get(self):
        url = request.args.get("url")
        if not url:
            raise BadRequest(description="Missing 'url' query parameter.")

        if not (url.startswith("http://") or url.startswith("https://")):
            raise BadRequest(description="Only http/https URLs are allowed.")

        try:
            req = Request(url, headers={"User-Agent": "DBMS-ImageProxy/1.0"})
            with urlopen(req, timeout=PROXY_TIMEOUT) as resp:
                body = resp.read()
                mimetype = resp.headers.get("Content-Type", "image/jpeg")
        except URLError as exc:
            raise BadGateway(description=f"Failed to fetch image: {exc}") from exc

        return Response(body, mimetype=mimetype)
