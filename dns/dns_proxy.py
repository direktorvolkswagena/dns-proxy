# Asynchronous DNS proxy server with blacklist filtering.

import asyncio
import json
import socket
import struct

def decode_qname(data: bytes, offset: int):
    labels = []
    jumped = False
    orig_offset = offset
    seen_offsets = set()

    while True:
        if offset >= len(data):
            raise ValueError("QNAME exceeds packet length")
        length = data[offset]
        # compression pointer: two-byte pointer
        if (length & 0xC0) == 0xC0:
            if offset + 1 >= len(data):
                raise ValueError("Truncated pointer in QNAME")
            pointer = ((length & 0x3F) << 8) | data[offset + 1]
            if pointer in seen_offsets:
                raise ValueError("Compression loop detected")
            seen_offsets.add(pointer)
            offset = pointer
            if not jumped:
                orig_offset += 2
                jumped = True
            continue
        offset += 1
        if length == 0:
            break
        label = data[offset:offset + length].decode('ascii', errors='ignore')
        labels.append(label)
        offset += length

    name = ".".join(labels)
    return name, (orig_offset if jumped else offset)


def encode_qname(name: str) -> bytes:
    if not name:
        return b'\x00'
    result = bytearray()
    for part in name.split('.'):
        part_bytes = part.encode('ascii')
        result.append(len(part_bytes))
        result.extend(part_bytes)
    result.append(0)
    return bytes(result)


def parse_question_section(data: bytes, qdcount: int, offset: int):
    questions = []
    for _ in range(qdcount):
        qname, offset = decode_qname(data, offset)
        if offset + 4 > len(data):
            raise ValueError("Truncated question section")
        qtype, qclass = struct.unpack_from("!HH", data, offset)
        offset += 4
        questions.append((qname, qtype, qclass))
    return questions, offset


def domain_matches_blacklist(domain: str, blacklist):
    domain = domain.lower().rstrip('.')
    for b in blacklist:
        b = b.lower().rstrip('.')
        if domain == b or domain.endswith('.' + b):
            return True
    return False


def build_header(tid, flags, qdcount, ancount=0):
    return struct.pack("!H H H H H H", tid, flags, qdcount, ancount, 0, 0)


def build_response(request, rcode=0, answer_ip=None):
    tid = struct.unpack_from("!H", request, 0)[0]
    flags_in = struct.unpack_from("!H", request, 2)[0]
    RD = flags_in & 0x0100
    QR, RA = 0x8000, 0x0080
    flags_out = QR | RD | RA | rcode

    qdcount = struct.unpack_from("!H", request, 4)[0]
    header = build_header(tid, flags_out, qdcount, 1 if answer_ip else 0)
    qsection = request[12:]

    if not answer_ip:
        return header + qsection  # NXDOMAIN / REFUSED case

    # Build A record (redirect)
    answer = bytearray()
    answer.extend(struct.pack("!H", 0xC00C))       # Name pointer
    answer.extend(struct.pack("!H", 1))            # TYPE = A
    answer.extend(struct.pack("!H", 1))            # CLASS = IN
    answer.extend(struct.pack("!I", 300))          # TTL
    answer.extend(struct.pack("!H", 4))            # RDLENGTH
    answer.extend(socket.inet_aton(answer_ip))     # RDATA
    return header + qsection + bytes(answer)

class AsyncDNSProxy:
    def __init__(self, upstream, blacklist, mode, redirect_ip=None):
        self.upstream = upstream
        self.blacklist = blacklist
        self.mode = mode
        self.redirect_ip = redirect_ip
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        print("[+] DNS proxy started.")

    def datagram_received(self, data, addr):
        asyncio.create_task(self.handle_request(data, addr))

    async def handle_request(self, data, client_addr):
        try:
            # Parse domain name
            qdcount = struct.unpack_from("!H", data, 4)[0]
            questions, _ = parse_question_section(data, qdcount, 12)
            qname = questions[0][0]
        except Exception:
            # If parsing fails, forward it to upstream
            await self.forward_to_upstream(data, client_addr)
            return

        if domain_matches_blacklist(qname, self.blacklist):
            if self.mode == "nxdomain":
                resp = build_response(data, rcode=3)
            elif self.mode == "refused":
                resp = build_response(data, rcode=5)
            elif self.mode == "redirect":
                resp = build_response(data, rcode=0, answer_ip=self.redirect_ip or "127.0.0.1")
            else:
                resp = build_response(data, rcode=3)
            self.transport.sendto(resp, client_addr)
            print(f"[BLOCKED] {qname} → mode={self.mode}")
            return

        # Otherwise forward upstream
        await self.forward_to_upstream(data, client_addr)

    async def forward_to_upstream(self, data, client_addr):
        try:
            loop = asyncio.get_event_loop()
            on_con_lost = loop.create_future()
            transport, protocol = await loop.create_datagram_endpoint(
                lambda: UpstreamClientProtocol(data, client_addr, self.transport, on_con_lost),
                remote_addr=self.upstream,
            )
            try:
                await asyncio.wait_for(on_con_lost, timeout=3.0)
            finally:
                transport.close()
        except asyncio.TimeoutError:
            # Upstream timeout → send SERVFAIL
            resp = build_response(data, rcode=2)
            self.transport.sendto(resp, client_addr)


class UpstreamClientProtocol(asyncio.DatagramProtocol):
    def __init__(self, query_data, client_addr, client_transport, on_con_lost):
        self.query_data = query_data
        self.client_addr = client_addr
        self.client_transport = client_transport
        self.on_con_lost = on_con_lost

    def connection_made(self, transport):
        transport.sendto(self.query_data)

    def datagram_received(self, data, addr):
        self.client_transport.sendto(data, self.client_addr)
        self.on_con_lost.set_result(True)

    def error_received(self, exc):
        self.on_con_lost.set_result(True)


async def main():
    with open("config.json", "r", encoding="utf-8") as f:
        cfg = json.load(f)

    listen = cfg.get("listen", "0.0.0.0:1053")
    host, port = listen.split(":")
    port = int(port)
    upstream = cfg.get("upstream", "8.8.8.8:53").split(":")
    upstream = (upstream[0], int(upstream[1]))
    mode = cfg.get("mode", "nxdomain")
    blacklist = cfg.get("blacklist", [])
    redirect_ip = cfg.get("redirect_ip")

    print(f"Listening on {host}:{port}, upstream {upstream}, mode={mode}")

    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: AsyncDNSProxy(upstream, blacklist, mode, redirect_ip),
        local_addr=(host, port),
    )
    try:
        await asyncio.sleep(3600 * 24)  # run forever
    finally:
        transport.close()


if __name__ == "__main__":
    asyncio.run(main())
