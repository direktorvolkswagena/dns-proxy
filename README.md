# Simple DNS Proxy Server with Blacklist
 
It sits between clients and an upstream DNS server, filtering requests based on a configurable blacklist, caching responses, and responding according to selected modes.

---

## Overview

This proxy server:
- Handles DNS requests over **UDP** asynchronously using `asyncio`
- Reads configuration from a **JSON file (`config.json`)**
- Supports **three blocking modes** for blacklisted domains:
  - `nxdomain` — respond as if the domain doesn’t exist  
  - `refused` — respond with REFUSED status  
  - `redirect` — respond with a fake A record pointing to a configured IP
- Includes an **in-memory DNS cache** to reduce upstream load and latency

---

## Features

| Feature | Description |
|----------|-------------|
| **Asynchronous I/O** | Uses `asyncio` for handling multiple DNS queries concurrently |
| **Configurable via JSON** | No code editing required — all behavior defined in `config.json` |
| **Blacklist filtering** | Filters specified domains locally before querying upstream |
| **Multiple modes** | `nxdomain`, `refused`, or `redirect` modes for handling blocked domains |
| **Lightweight** | No third-party libraries used for DNS packet parsing |

---

## Configuration (`config.json`)

Example:

```json
{
  "listen": "0.0.0.0:1053",
  "upstream": "8.8.8.8:53",
  "mode": "redirect",
  "blacklist": ["ads.example.com", "tracking.site.com"],
  "redirect_ip": "127.0.0.1"
}
```

Configuration Fields:

| Key | Type | Description | Default |
| :--- | :--- | :--- | :--- |
| `listen` | string | IP and port for proxy to listen on | `"0.0.0.0:1053"` |
| `upstream` | string | IP and port of upstream DNS server | `"8.8.8.8:53"` |
| `mode` | string | Defines how to respond to blacklisted domains | `"nxdomain"` |
| `blacklist` | array | List of blacklisted domains (exact matches) | `[]` |
| `redirect_ip` | string | IP address to use when in `redirect` mode | `None` |

## Installation

**Prerequisites:**

Python 3.10+
No external libraries required (only standard library modules)

**Steps:**

- Clone or download this project.
- Ensure your working directory contains:

    ```bash
    dns_proxy.py
    config.json
    ```

- Run the server:

    ```bash
    python3 dns_proxy.py
    ```

- You should see output like:

    ```bash
    Listening on 0.0.0.0:1053
    Using upstream DNS: 8.8.8.8:53
    Mode: redirect
    ```

## Testing

- **Functional test** - Query a non-blacklisted domain:

    ```bash
    dig @127.0.0.1 -p 1053 example.com
    ```

- **Blacklist test** - Add "example.com" to the blacklist array in config.json:

    Test again:

    ```bash
    dig @127.0.0.1 -p 1053 example.com
    ```

- **Load test** - simulation of multiple concurrent requests using a custom bash script with `dnsperf` tool:

    ```bash
    ./server_test/flood.sh
    ```

    Script prompts user:

    ```text
    Enter the query data file path: 
    Enter the test duration in seconds: 
    Enter the maximum query rate: 
    ```

    `Query data` is a text file with blocked domains of format:

    ```text
    server_fqdn record_type direction
    ```

    _In our case record_type is always 'A' and direction is always IN. For testing purposes a "queries.txt" file is included in repo_

    Example output:

    ```bash
    --- Starting dnsperf Test ---
    Server: 127.0.0.1 (Port: 1053)
    Query File: server_test/queries.txt
    Duration (seconds): 30
    Query Rate (QPS): 500
    -----------------------------

    DNS Performance Testing Tool
    Version 2.14.0

    [Status] Command line: dnsperf -s 127.0.0.1 -p 1053 -d server_test/queries.txt -l 30 -Q 500
    [Status] Sending queries (to 127.0.0.1:1053)
    [Status] Started at: Tue Oct 21 20:23:15 2025
    [Status] Stopping after 30.000000 seconds
    [Status] Testing complete (time limit)

    Statistics:

        Queries sent:         2539
        Queries completed:    2539 (100.00%)
        Queries lost:         0 (0.00%)

        Response codes:       NOERROR 1539 (60.61%), SERVFAIL 1000 (39.39%)
        Average packet size:  request 29, response 39
        Run time (s):         30.647059
        Queries per second:   82.846449

        Average Latency (s):  1.182856 (min 0.000097, max 3.005807)
        Latency StdDev (s):   1.466489


    Test completed successfully.

    ```

## Known Limitations and Restrictions

| **Area** | **Description** |
|------|--------------|
| Protocol | Supports only UDP-based DNS. TCP DNS, DNS-over-HTTPS (DoH), and DNS-over-TLS (DoT) are not implemented. |
| DNS parsing | DNS packets are built and parsed manually. Only basic query/response types are supported. Features like EDNS, compression pointers, and DNSSEC are not handled. |
| Blacklist matching | Blacklist uses exact string matching. Wildcards (`*.example.com`) or regular expressions are not supported. |
| Single upstream server | Only one upstream DNS server can be configured. There is no failover or load balancing. |
| No concurrency limits | Asyncio handles multiple clients concurrently, but there is no rate limiting or connection throttling to prevent overload. |
| No DNSSEC validation | DNSSEC signatures are not verified; the proxy simply forwards and modifies DNS packets as plain data. |
| No TCP fallback | Large DNS packets (>512 bytes) that require TCP fallback will not be handled correctly. |
| No hot-reload of configuration | Changes to `config.json` require a manual restart of the proxy. |
| Limited error handling | Upstream timeouts or network errors may cause dropped queries. There is no retry or exponential backoff. |
| No logging or monitoring | The server lacks structured logging, metrics, or debugging levels. Only basic `print()` statements are used. |
| Security | The proxy has no authentication or encryption. It trusts all clients that can reach it. Should not be exposed publicly without firewall protection. |
| IPv6 support | Currently supports IPv4 A records only. IPv6 sockets and AAAA record handling are not implemented. |
