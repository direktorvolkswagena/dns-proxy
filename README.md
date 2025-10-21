# dns-proxy

# DNS Proxy Server with Blacklist
 
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
| **Caching** | Caches DNS responses for performance |
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

## Installation

Prerequisites:

Python 3.10+
No external libraries required (only standard library modules)

Steps:

1) Clone or download this project.
  
Ensure your working directory contains:
