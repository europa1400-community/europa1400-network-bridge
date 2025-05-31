import asyncio
import logging
import socket
import struct
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

            self._apply_socket_tweaks(writer)
            self._apply_socket_tweaks(target_writer)

            async def proxmox_style_pipe(
                src: StreamReader, dst: StreamWriter, label: str
            ):
                try:
                    while True:
                        data = await src.read(1024)
                        if not data:
                            logging.info(f"{label}: EOF from source")
                            break

                        # Split data into small chunks (like Proxmox TCP stack might)
                        for i in range(0, len(data), 128):
                            chunk = data[i : i + 128]
                            dst.write(chunk)
                            await dst.drain()
                            await asyncio.sleep(
                                0.001
                            )  # Delay to simulate real PSH timing
                            logging.debug(f"{label}: forwarded {len(chunk)} bytes")
                except Exception as e:
                    logging.warning(f"{label}: exception: {e}")
                finally:
                    logging.info(f"{label}: closing destination")
                    dst.close()
                    await dst.wait_closed()

            await asyncio.gather(
                proxmox_style_pipe(reader, target_writer, "client → server"),
                proxmox_style_pipe(target_reader, writer, "server → client"),
                return_exceptions=False,
            )

        except Exception as e:
            logging.error(f"Bridge error: {e}")
        finally:
            logging.info("Connection closed.")
            writer.close()
            await writer.wait_closed()

    def _apply_socket_tweaks(self, writer: StreamWriter) -> None:
        sock = writer.get_extra_info("socket")
        if sock:
            # Disable Nagle
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

            # Set SO_LINGER to 2s to flush remaining data
            linger_struct = struct.pack("ii", 1, 2)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, linger_struct)

            # Enable keepalive
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

            logging.debug(f"Socket tweaks applied to {sock.getsockname()}")
