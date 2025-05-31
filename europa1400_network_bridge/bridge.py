import asyncio
import logging
import socket
from asyncio import StreamReader, StreamWriter
from typing import Tuple

from europa1400_network_bridge.config import Config


class NetworkBridge:
    def __init__(self, config: Config) -> None:
        self.config = config

    def _determine_ports_and_address(self) -> Tuple[str, int, str, int]:
        if self.config.is_server:
            return (
                "0.0.0.0",
                self.config.network_bridge_port,
                "127.0.0.1",
                self.config.gilde_port,
            )
        else:
            return (
                "127.0.0.1",
                self.config.gilde_port,
                self.config.target,
                self.config.network_bridge_port,
            )

    async def run(self) -> None:
        listen_host, listen_port, target_host, target_port = (
            self._determine_ports_and_address()
        )

        server = await asyncio.start_server(
            lambda r, w: self._handle_connection(r, w, target_host, target_port),
            listen_host,
            listen_port,
        )

        addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
        mode = "server" if self.config.is_server else "client"
        logging.info(
            f"Bridge running in {mode} mode. Listening on {addrs}, forwarding to {target_host}:{target_port}"
        )

        async with server:
            await server.serve_forever()

    async def _handle_connection(
        self,
        reader: StreamReader,
        writer: StreamWriter,
        target_host: str,
        target_port: int,
    ) -> None:
        peername = writer.get_extra_info("peername")
        logging.info(
            f"Incoming connection from {peername} → {target_host}:{target_port}"
        )

        try:
            target_reader, target_writer = await asyncio.open_connection(
                target_host, target_port
            )

            self._disable_nagle(writer)
            self._disable_nagle(target_writer)

            async def pipe(src: StreamReader, dst: StreamWriter, label: str):
                try:
                    while True:
                        data = await src.read(8192)
                        if not data:
                            logging.info(f"{label}: EOF from source")
                            break
                        logging.debug(f"{label}: forwarding {len(data)} bytes")
                        dst.write(data)
                        await dst.drain()
                except Exception as e:
                    logging.warning(f"{label}: exception: {e}")
                    raise  # Important: propagate to cancel other pipe!
                finally:
                    logging.info(f"{label}: closing destination")
                    dst.close()
                    await dst.wait_closed()

            await asyncio.gather(
                pipe(reader, target_writer, "client → server"),
                pipe(target_reader, writer, "server → client"),
                return_exceptions=False,  # Fail fast if one breaks
            )

        except Exception as e:
            logging.error(f"Bridge error: {e}")
        finally:
            logging.info("Connection closed.")
            writer.close()
            await writer.wait_closed()

    def _disable_nagle(self, writer: StreamWriter) -> None:
        sock = writer.get_extra_info("socket")
        if sock:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            value = sock.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY)
            logging.debug(f"Set TCP_NODELAY: {value} on {sock.getsockname()}")
