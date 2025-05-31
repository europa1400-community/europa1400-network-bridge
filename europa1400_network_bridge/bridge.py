import asyncio
import logging
import socket
from asyncio import StreamReader, StreamWriter
from typing import Tuple

from europa1400_network_bridge.config import Config


class NetworkBridge:
    def __init__(self, config: Config) -> None:
        self.config = config
        self._should_run = True

    def _determine_ports_and_address(self) -> Tuple[str, int, str, int]:
        if self.config.is_server:
            listen_host = "0.0.0.0"
            listen_port = self.config.network_bridge_port
            target_host = "127.0.0.1"
            target_port = self.config.gilde_port
        else:
            listen_host = "127.0.0.1"
            listen_port = self.config.gilde_port
            target_host = self.config.target
            target_port = self.config.network_bridge_port
        return listen_host, listen_port, target_host, target_port

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

        try:
            async with server:
                await server.serve_forever()
        except asyncio.CancelledError:
            logging.info("Bridge shutdown requested.")
            raise

    async def _handle_connection(
        self,
        reader: StreamReader,
        writer: StreamWriter,
        target_host: str,
        target_port: int,
    ) -> None:
        peername = writer.get_extra_info("peername")
        logging.info(
            f"Incoming connection from {peername} -> forwarding to {target_host}:{target_port}"
        )

        try:
            target_reader, target_writer = await asyncio.open_connection(
                target_host, target_port
            )

            self._disable_nagle(writer)
            self._disable_nagle(target_writer)

            async def pipe(
                src_reader: StreamReader, dest_writer: StreamWriter, direction: str
            ):
                try:
                    while True:
                        data = await src_reader.read(8192)
                        if not data:
                            logging.info(f"{direction}: connection closed")
                            break
                        dest_writer.write(data)
                        await dest_writer.drain()
                except Exception as e:
                    logging.warning(f"{direction} pipe error: {e}")
                finally:
                    dest_writer.close()
                    await dest_writer.wait_closed()

            await asyncio.gather(
                pipe(reader, target_writer, "client_to_target"),
                pipe(target_reader, writer, "target_to_client"),
            )

        except Exception as e:
            logging.error(f"Connection error: {e}")
        finally:
            logging.info("Connection fully closed.")
            writer.close()
            await writer.wait_closed()

    def _disable_nagle(self, writer: StreamWriter) -> None:
        sock = writer.get_extra_info("socket")
        if sock:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
