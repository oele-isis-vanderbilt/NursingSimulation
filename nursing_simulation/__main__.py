from aiohttp import web

from nursing_simulation.webrtc_service import WebRTCService


def get_webrtc_app(args=None):
    service = WebRTCService(
        host=args.host,
        port=args.port,
        mode=args.mode,
    )

    app = service.get_app()

    return app


def main():
    import logging

    logging.basicConfig(level=logging.INFO)
    from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser

    parser = ArgumentParser(
        description="WebRTC service",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("command", choices=["webrtc"], help="Command to run")

    parser.add_argument(
        "--host",
        "-H",
        type=str,
        default="localhost",
        help="Host to serve to",
    )

    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=8080,
        help="Port to serve to",
    )

    parser.add_argument(
        "--mode",
        "-m",
        type=str,
        choices=["dev", "prod"],
        default="dev",
        help="Mode to run in",
    )

    args = parser.parse_args()

    if args.command == "webrtc":
        app = get_webrtc_app(args)
        web.run_app(app, host=args.host, port=args.port)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
