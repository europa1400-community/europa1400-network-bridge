import asyncio
import logging
from asyncio import StreamReader, StreamWriter
from typing import Tuple

from europa1400_network_bridge.config import Config


class NetworkBridge:
    def __init__(self, config: Config) -> None:
        self.config = config
        self._should_run = True

    def _determine_ports_and_address(self) -> Tuple[str, int, int]:
        if self.config.is_server:
            listen_host = "0.0.0.0"
            listen_port = self.config.network_bridge_port
            target_port = self.config.gilde_port
        else:
            listen_host = "127.0.0.1"
            listen_port = self.config.gilde_port
            target_port = self.config.network_bridge_port
        return listen_host, listen_port, target_port

    async def run(self) -> None:
        listen_host, listen_port, target_port = self._determine_ports_and_address()

        server = await asyncio.start_server(
            lambda r, w: self._handle_connection(r, w, target_port),
            listen_host,
            listen_port,
        )

        addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
        logging.info(
            f"Bridge started. Listening on {addrs}, forwarding to {self.config.target}:{target_port}"
        )

        try:
            async with server:
                await server.serve_forever()
        except asyncio.CancelledError:
            logging.info("Network bridge has been shut down.")
            raise

    async def _handle_connection(
        self, reader: StreamReader, writer: StreamWriter, target_port: int
    ) -> None:
        try:
            target_reader, target_writer = await asyncio.open_connection(
                self.config.target, target_port
            )
            logging.info(
                f"New incoming connection from {writer.get_extra_info('peername')} -> forwarding to {self.config.target}:{target_port}"
            )

            async def gilde_to_bridge():
                try:
                    while True:
                        payload = await reader.read(1048574)
                        if not payload:
                            logging.info("gilde_to_bridge: connection closed by peer")
                            break
                        logging.debug(
                            f"gilde_to_bridge: forwarding {len(payload)} bytes"
                        )
                        length = len(payload).to_bytes(8, byteorder="big")
                        target_writer.write(length + payload)
                        await target_writer.drain()
                except Exception as e:
                    logging.info(f"gilde_to_bridge closed with error: {e}")

            async def bridge_to_gilde():
                try:
                    while True:
                        length_bytes = await target_reader.readexactly(8)
                        length = int.from_bytes(length_bytes, byteorder="big")
                        payload = await target_reader.readexactly(length)
                        logging.debug(f"bridge_to_gilde: forwarding {length} bytes")
                        writer.write(payload)
                        await writer.drain()
                except Exception as e:
                    logging.info(f"bridge_to_gilde closed with error: {e}")

            if self.config.is_server:
                await asyncio.gather(bridge_to_gilde(), gilde_to_bridge())
            else:
                await asyncio.gather(gilde_to_bridge(), bridge_to_gilde())

        except Exception as e:
            logging.error(f"Connection setup error: {e}")
        finally:
            logging.info("Closing connection")
            writer.close()
            await writer.wait_closed()
