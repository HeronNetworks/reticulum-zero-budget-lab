# Zero-Budget Reticulum Deployment Guide

> A complete, reproducible walkthrough for setting up a 3-node Reticulum mesh
> network on a single Windows machine using only TCP/IP, connecting to the live
> public Reticulum network, and sending end-to-end encrypted messages between
> nodes — all with zero cost.

**Test environment:**

| Component | Value                           |
|-----------|---------------------------------|
| OS        | Windows 10 Home 10.0.19045      |
| Python    | 3.12.8                          |
| Shell     | Git Bash (MINGW64)              |
| RNS       | 1.1.3                           |
| LXMF      | 0.9.4                           |
| NomadNet  | 0.9.8                           |
| Date      | 2026-03-01                      |

---

## Table of Contents

1.  [Background: What Is Reticulum?](#1-background-what-is-reticulum)
2.  [Install Reticulum](#2-install-reticulum)
3.  [Generate and Examine the Default Config](#3-generate-and-examine-the-default-config)
4.  [Design the 3-Node Topology](#4-design-the-3-node-topology)
5.  [Write the Node Configs](#5-write-the-node-configs)
6.  [Start All Nodes](#6-start-all-nodes)
7.  [Verify Connectivity](#7-verify-connectivity)
8.  [Connect to the Public Reticulum Network](#8-connect-to-the-public-reticulum-network)
9.  [Install LXMF and Send Messages Between Nodes](#9-install-lxmf-and-send-messages-between-nodes)
10. [Diagnostic & Management Tools — Full Reference](#10-diagnostic--management-tools--full-reference)
11. [Troubleshooting](#11-troubleshooting)
12. [Files Created](#12-files-created)
13. [Quick-Start Cheat Sheet](#13-quick-start-cheat-sheet)

---

## 1. Background: What Is Reticulum?

Reticulum is a cryptography-based networking stack designed for building
reliable, encrypted networks over any medium — LoRa radios, packet radio, WiFi,
TCP/IP, I2P, serial links, or even carrier pigeons. Key properties:

- **Identity-based addressing** — no IP addresses. Every node has a
  cryptographic identity (an Ed25519/X25519 keypair). Addresses are derived
  from the public key hash.
- **End-to-end encryption by default** — all communication is encrypted.
  There is no unencrypted mode.
- **Transport routing** — nodes with `enable_transport = Yes` relay traffic
  for other nodes. Leaf nodes only send/receive their own traffic.
- **Shared instances** — on a single machine, one `rnsd` process opens
  the hardware/network interfaces and other programs connect to it via a
  local socket (or on Windows, a local TCP port).
- **LXMF** (Lightweight Extensible Message Format) — a store-and-forward
  messaging protocol built on top of Reticulum, used by NomadNet and
  Sideband.

In this guide we use **TCP/IP only** (no radio hardware needed) to build a
fully functional 3-node mesh on one machine, then connect it to the live
global Reticulum network.

---

## 2. Install Reticulum

### 2.1 Install the core package

```bash
pip install rns
```

```
Collecting rns
  Downloading rns-1.1.3-py3-none-any.whl.metadata (23 kB)
Collecting cryptography>=3.4.7 (from rns)
  Downloading cryptography-46.0.5-cp311-abi3-win_amd64.whl.metadata (5.7 kB)
Collecting pyserial>=3.5 (from rns)
  Downloading pyserial-3.5-py2.py3-none-any.whl.metadata (1.6 kB)
Collecting cffi>=2.0.0 (from cryptography>=3.4.7->rns)
  Downloading cffi-2.0.0-cp312-cp312-win_amd64.whl.metadata (2.6 kB)
...
Successfully installed cffi-2.0.0 cryptography-46.0.5 pyserial-3.5 rns-1.1.3
```

Dependencies pulled in automatically: `cryptography` (for the crypto
primitives) and `pyserial` (for serial/radio interfaces — unused here but
required).

### 2.2 Verify the installed CLI tools

```bash
$ rnsd --version
rnsd 1.1.3

$ rnstatus --version
rnstatus 1.1.3

$ rnpath --version
rnpath 1.1.3

$ rnprobe --version
rnprobe 1.1.3

$ rnid --version
rnid 1.1.3
```

Five CLI tools ship with `rns`:

| Tool       | Purpose                                                  |
|------------|----------------------------------------------------------|
| `rnsd`     | Reticulum daemon — runs the network stack                |
| `rnstatus` | Shows interface status, traffic, transport info          |
| `rnpath`   | Views/manages the routing table                          |
| `rnprobe`  | Ping-like probe for testing transport node reachability  |
| `rnid`     | Identity management, file encryption, signing            |

### 2.3 Package details

```
Name: rns
Version: 1.1.3
Summary: Self-configuring, encrypted and resilient mesh networking stack
         for LoRa, packet radio, WiFi and everything in between
Home-page: https://reticulum.network/
Author: Mark Qvist
Requires: cryptography, pyserial
```

---

## 3. Generate and Examine the Default Config

### 3.1 First run — generate config

Running `rnsd` for the first time creates `~/.reticulum/` with a default
configuration:

```bash
$ rnsd &
$ sleep 3
$ kill $!
```

### 3.2 What gets created

```
~/.reticulum/
├── config          # Main configuration file (INI-like format)
├── interfaces/     # Per-interface persistent storage
└── storage/        # Identity keys, path table, caches
```

### 3.3 Default config — annotated

```ini
[reticulum]

  # Transport is OFF by default. Only turn it on for nodes that should
  # relay traffic for others (and are always-on / stationary).
  enable_transport = False

  # Shared instance mode: the first rnsd process opens all interfaces,
  # and other programs (rnstatus, nomadnet, etc.) connect to it via
  # a local socket. This should almost always be Yes.
  share_instance = Yes

  # Instance name — used for domain socket naming on Unix.
  # On Windows, this is less relevant because ports are used instead.
  instance_name = default

[logging]
  # 0=critical, 1=error, 2=warning, 3=notice, 4=info, 5=verbose,
  # 6=debug, 7=extreme
  loglevel = 4

[interfaces]

  # AutoInterface: uses IPv6 link-local multicast for zero-config
  # LAN peer discovery. No routers or DHCP needed.
  [[Default Interface]]
    type = AutoInterface
    enabled = Yes
```

The `AutoInterface` is great for LAN discovery but we don't need it for our
TCP-only lab. We'll replace it entirely.

### 3.4 Full example config

The complete example config with every option documented is 472 lines long.
Generate it with:

```bash
rnsd --exampleconfig > example_config.txt
```

This shows examples for all interface types: `AutoInterface`,
`UDPInterface`, `TCPServerInterface`, `TCPClientInterface`, `I2PInterface`,
`RNodeInterface`, and more. A copy is saved in the guide directory as
`example_config_full.txt`.

---

## 4. Design the 3-Node Topology

### 4.1 Architecture diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Public Reticulum Network                      │
│         (BetweenTheBorders Hub, 20+ community nodes)            │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ TCP outbound to
                            │ reticulum.betweentheborders.com:4242
                            │
             ┌──────────────┴──────────────┐
             │           NODE 1            │
             │                             │
             │  Role: Transport Node       │
             │  Interfaces:                │
             │   - TCPServer 127.0.0.1:4242│
             │   - TCPClient → public hub  │
             │  Ports: 37428 / 37429       │
             │  Transport: YES             │
             │  Probe responder: YES       │
             └──────┬──────────┬───────────┘
                    │          │
           TCP :4242│          │TCP :4242
                    │          │
             ┌──────┴──┐  ┌───┴──────┐
             │ NODE 2  │  │  NODE 3  │
             │         │  │          │
             │ Leaf    │  │  Leaf    │
             │ TCP     │  │  TCP     │
             │ Client  │  │  Client  │
             │ :37430  │  │  :37432  │
             └─────────┘  └──────────┘
```

### 4.2 Role assignments

| Node | Role | Transport? | Interfaces | Purpose |
|------|------|:----------:|------------|---------|
| Node1 | Hub / Gateway | Yes | TCP Server + TCP Client (public) | Routes all traffic, bridges to public net |
| Node2 | Leaf | No | TCP Client → Node1 | LXMF message receiver |
| Node3 | Leaf | No | TCP Client → Node1 | LXMF message sender |

### 4.3 Windows-specific: port isolation

On Linux/macOS, Reticulum uses Unix domain sockets to isolate shared
instances. **Windows does not support domain sockets**, so Reticulum falls
back to local TCP ports. Each node needs a **unique pair of ports**:

| Node  | `shared_instance_port` | `instance_control_port` | Notes |
|-------|:----------------------:|:-----------------------:|-------|
| node1 | 37428 | 37429 | Default ports |
| node2 | 37430 | 37431 | +2 offset |
| node3 | 37432 | 37433 | +4 offset |

The `shared_instance_port` is where other local programs (like `rnstatus`)
connect to talk to the running `rnsd`. The `instance_control_port` is for
management commands. **If two nodes use the same ports, one will fail to
start silently.**

### 4.4 Create the config directories

```bash
$ mkdir -p ~/reticulum-guide/node1
$ mkdir -p ~/reticulum-guide/node2
$ mkdir -p ~/reticulum-guide/node3
```

Each directory will become a self-contained Reticulum home with its own
identity, storage, and interfaces — as if it were a separate machine.

---

## 5. Write the Node Configs

### 5.1 Node1 — Transport Node + TCP Server + Public Gateway

**File: `configs/node1/config`**

```ini
[reticulum]
  enable_transport = Yes
  share_instance = Yes
  shared_instance_port = 37428
  instance_control_port = 37429
  respond_to_probes = Yes

[logging]
  loglevel = 5

[interfaces]
  [[TCP Server Interface]]
    type = TCPServerInterface
    enabled = Yes
    listen_ip = 127.0.0.1
    listen_port = 4242

  [[BetweenTheBorders Hub]]
    type = TCPClientInterface
    enabled = Yes
    target_host = reticulum.betweentheborders.com
    target_port = 4242
```

**Line-by-line breakdown:**

| Setting | Value | Why |
|---------|-------|-----|
| `enable_transport` | `Yes` | Makes Node1 a relay — it forwards packets between Node2, Node3, and the public network |
| `respond_to_probes` | `Yes` | Enables the `rnprobe` diagnostic tool to ping this node |
| `shared_instance_port` | `37428` | Local port where `rnstatus` etc. connect |
| `loglevel` | `5` | Verbose logging so we can see what's happening |
| `TCPServerInterface` | `127.0.0.1:4242` | Listens for incoming connections from Node2/Node3 |
| `TCPClientInterface` | `betweentheborders:4242` | Connects outbound to the public network |

### 5.2 Node2 — Leaf Node (Message Receiver)

**File: `configs/node2/config`**

```ini
[reticulum]
  enable_transport = No
  share_instance = Yes
  shared_instance_port = 37430
  instance_control_port = 37431

[logging]
  loglevel = 5

[interfaces]
  [[TCP Client to Node1]]
    type = TCPClientInterface
    enabled = Yes
    target_host = 127.0.0.1
    target_port = 4242
```

### 5.3 Node3 — Leaf Node (Message Sender)

**File: `configs/node3/config`**

```ini
[reticulum]
  enable_transport = No
  share_instance = Yes
  shared_instance_port = 37432
  instance_control_port = 37433

[logging]
  loglevel = 5

[interfaces]
  [[TCP Client to Node1]]
    type = TCPClientInterface
    enabled = Yes
    target_host = 127.0.0.1
    target_port = 4242
```

Node2 and Node3 are identical except for their ports. They are leaf nodes —
they only handle their own traffic and rely on Node1 to route everything.

---

## 6. Start All Nodes

### 6.1 Critical: set UTF-8 encoding on Windows

Reticulum's CLI tools use Unicode arrows (↑↓) and spinners (⢄⢂⡁...) in
their output. The Windows console defaults to cp1252, which cannot render
these characters and will crash with:

```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2191'
  in position 16: character maps to <undefined>
```

**Fix — run this before every session:**

```bash
export PYTHONIOENCODING=utf-8
```

> **Tip:** Add this to your `~/.bashrc` or `~/.bash_profile` to make it
> permanent.

### 6.2 Start Node1 first (it's the server)

```bash
$ rnsd --config ~/reticulum-guide/node1 &
```

Wait ~8 seconds for the TCP server to bind and the public hub connection to
establish (DNS resolution + TCP handshake + Reticulum handshake).

### 6.3 Start Node2 and Node3

```bash
$ rnsd --config ~/reticulum-guide/node2 &
$ rnsd --config ~/reticulum-guide/node3 &
$ sleep 5
```

### 6.4 Verify all three are running

You can check with `netstat`:

```bash
$ netstat -ano | grep -E "37428|37430|37432"
TCP    127.0.0.1:37428    0.0.0.0:0    LISTENING    <pid>
TCP    127.0.0.1:37430    0.0.0.0:0    LISTENING    <pid>
TCP    127.0.0.1:37432    0.0.0.0:0    LISTENING    <pid>
```

All three shared instance ports should show `LISTENING`.

---

## 7. Verify Connectivity

### 7.1 `rnstatus` — Node1 (Transport + Public Gateway)

```bash
$ rnstatus --config ~/reticulum-guide/node1
```

```
 Shared Instance[37428]
    Status    : Up
    Serving   : 0 programs
    Rate      : 1.00 Gbps
    Traffic   : ↑0 B  0 bps
                ↓0 B  0 bps

 TCPServerInterface[TCP Server Interface/127.0.0.1:4242]
    Status    : Up
    Clients   : 2
    Mode      : Full
    Rate      : 10.00 Mbps
    Traffic   : ↑0 B    0 bps
                ↓390 B  0 bps

 TCPInterface[BetweenTheBorders Hub/reticulum.betweentheborders.com:4242]
    Status    : Up
    Mode      : Full
    Rate      : 10.00 Mbps
    Traffic   : ↑838 B  0 bps
                ↓617 B  0 bps

 Transport Instance <91e8c5eaaefbb5b0014a2b448f538349> running
 Probe responder at <a7f8b69872d97d16ab5bd64d2e90de3b> active
 Uptime is 20.43s
```

**What to look for:**
- `Clients : 2` on the TCP Server — both leaf nodes connected
- `Status : Up` on the BetweenTheBorders Hub — public network connected
- `Transport Instance ... running` — this node is relaying traffic
- `Probe responder ... active` — `rnprobe` will work against this node

### 7.2 `rnstatus` — Node2 (Leaf)

```bash
$ rnstatus --config ~/reticulum-guide/node2
```

```
 Shared Instance[37430]
    Status    : Up
    Serving   : 0 programs
    Rate      : 1.00 Gbps
    Traffic   : ↑0 B  0 bps
                ↓0 B  0 bps

 TCPInterface[TCP Client to Node1/127.0.0.1:4242]
    Status    : Up
    Mode      : Full
    Rate      : 10.00 Mbps
    Traffic   : ↑198 B  0 bps
                ↓0 B    0 bps
```

### 7.3 `rnstatus` — Node3 (Leaf)

```bash
$ rnstatus --config ~/reticulum-guide/node3
```

```
 Shared Instance[37432]
    Status    : Up
    Serving   : 0 programs
    Rate      : 1.00 Gbps
    Traffic   : ↑0 B  0 bps
                ↓0 B  0 bps

 TCPInterface[TCP Client to Node1/127.0.0.1:4242]
    Status    : Up
    Mode      : Full
    Rate      : 10.00 Mbps
    Traffic   : ↑198 B  0 bps
                ↓0 B    0 bps
```

### 7.4 `rnstatus -a` — Show ALL interfaces (including internal)

The `-a` flag reveals hidden internal interfaces that `rnstatus` normally
omits:

```bash
$ rnstatus --config ~/reticulum-guide/node1 -a
```

```
 Shared Instance[37428]
    Status    : Up
    Serving   : 0 programs
    Rate      : 1.00 Gbps
    Traffic   : ↑0 B  0 bps
                ↓0 B  0 bps

 TCPServerInterface[TCP Server Interface/127.0.0.1:4242]
    Status    : Up
    Clients   : 2
    Mode      : Full
    Rate      : 10.00 Mbps
    Traffic   : ↑0 B    0 bps
                ↓390 B  0 bps

 TCPInterface[BetweenTheBorders Hub/reticulum.betweentheborders.com:4242]
    Status    : Up
    Mode      : Full
    Rate      : 10.00 Mbps
    Traffic   : ↑432 B  0 bps
                ↓233 B  0 bps

 LocalInterface[52462]              <-- internal socket for local programs
    Status    : Up
    Rate      : 1.00 Gbps
    Traffic   : ↑0 B  0 bps
                ↓0 B  0 bps

 Transport Instance <91e8c5eaaefbb5b0014a2b448f538349> running
 Probe responder at <a7f8b69872d97d16ab5bd64d2e90de3b> active
```

Notice the `LocalInterface` — that's the local socket used by `rnstatus`
itself to talk to the running `rnsd` process.

### 7.5 `rnstatus -A` — Announce statistics

```bash
$ rnstatus --config ~/reticulum-guide/node1 -A
```

```
 Shared Instance[37428]
    Status    : Up
    Serving   : 0 programs
    Rate      : 1.00 Gbps
    Announces : 0.00 µHz↑
                0.00 µHz↓
    Traffic   : ↑0 B  0 bps
                ↓0 B  0 bps

 TCPServerInterface[TCP Server Interface/127.0.0.1:4242]
    Status    : Up
    Clients   : 2
    Mode      : Full
    Rate      : 10.00 Mbps
    Announces : 182.05 mHz↑
                0.00 µHz↓
    Traffic   : ↑857 B    0 bps
                ↓1.28 KB  0 bps

 TCPInterface[BetweenTheBorders Hub/reticulum.betweentheborders.com:4242]
    Status    : Up
    Mode      : Full
    Rate      : 10.00 Mbps
    Announces : 86.38 mHz↑
                55.70 mHz↓
    Traffic   : ↑838 B  0 bps
                ↓818 B  0 bps
```

The `Announces` lines show the rate of announce packets flowing through
each interface. The public hub is both sending (86.38 mHz) and receiving
(55.70 mHz) announces — these are other nodes on the network advertising
their destinations.

### 7.6 `rnstatus -t` — Traffic totals

```bash
$ rnstatus --config ~/reticulum-guide/node1 -t
```

Adds a `Totals` line at the bottom summing all interface traffic:

```
 Totals       : ↑1.50 KB  0 bps
                ↓2.10 KB  0 bps
```

### 7.7 `rnprobe` — Ping Node1 from Node2

`rnprobe` is Reticulum's equivalent of `ping`. It sends a probe packet to a
transport node's probe responder and measures round-trip time.

```bash
$ rnprobe --config ~/reticulum-guide/node2 -v -t 10 -n 3 \
    "rnstransport.probe" "a7f8b69872d97d16ab5bd64d2e90de3b"
```

```
Path to <a7f8b69872d97d16ab5bd64d2e90de3b> requested
Sent probe 1 (16 bytes) to <a7f8b69872d97d16ab5bd64d2e90de3b>
  via <a7f8b69872d97d16ab5bd64d2e90de3b>
  on TCPInterface[TCP Client to Node1/127.0.0.1:4242]
Valid reply from <a7f8b69872d97d16ab5bd64d2e90de3b>
Round-trip time is 1.993 milliseconds over 1 hop

Sent probe 2 (16 bytes) to <a7f8b69872d97d16ab5bd64d2e90de3b>
  ...
Valid reply from <a7f8b69872d97d16ab5bd64d2e90de3b>
Round-trip time is 0.0 milliseconds over 1 hop

Sent probe 3 (16 bytes) to <a7f8b69872d97d16ab5bd64d2e90de3b>
  ...
Valid reply from <a7f8b69872d97d16ab5bd64d2e90de3b>
Round-trip time is 0.996 milliseconds over 1 hop

Sent 3, received 3, packet loss 0.0%
```

**Key observations:**
- `1 hop` — Node2 → Node1 is a single hop (direct TCP connection)
- `~1 ms` round-trip — expected for localhost
- `0.0%` packet loss — perfect connectivity
- The probe responder hash (`a7f8b69872...`) is shown at rnsd startup

### 7.8 `rnprobe` — Ping Node1 from Node3

```bash
$ rnprobe --config ~/reticulum-guide/node3 -v -t 10 -n 3 \
    "rnstransport.probe" "a7f8b69872d97d16ab5bd64d2e90de3b"
```

```
Sent probe 1 (16 bytes) ... Round-trip time is 0.997 milliseconds over 1 hop
Sent probe 2 (16 bytes) ... Round-trip time is 0.997 milliseconds over 1 hop
Sent probe 3 (16 bytes) ... Round-trip time is 0.996 milliseconds over 1 hop

Sent 3, received 3, packet loss 0.0%
```

### 7.9 `rnpath` — View the routing table

```bash
$ rnpath --config ~/reticulum-guide/node2 -t
```

```
<a7f8b69872d97d16ab5bd64d2e90de3b> is 1 hop  away
  via <a7f8b69872d97d16ab5bd64d2e90de3b>
  on TCPInterface[TCP Client to Node1/127.0.0.1:4242]
  expires 2026-03-08 19:42:47
```

Node2 knows one path: to Node1's probe responder, 1 hop away. Paths expire
after 7 days by default.

```bash
$ rnpath --config ~/reticulum-guide/node1 -t
```

```
<00ba385df74a009e0322fb359d9b0e2b> is 4 hops away
  via <4923963ea77a06fe90289ca2fc051e4f>
  on TCPInterface[BetweenTheBorders Hub/reticulum.betweentheborders.com:4242]
  expires 2026-03-08 19:42:22
```

Node1 (the transport node) already knows about destinations on the **public
Reticulum network** — 4 hops away through the BetweenTheBorders transport
node. These are real, live nodes.

### 7.10 `rnpath` — Look up a specific destination

```bash
$ rnpath --config ~/reticulum-guide/node2 -v a7f8b69872d97d16ab5bd64d2e90de3b
```

```
Path to <a7f8b69872d97d16ab5bd64d2e90de3b> requested  ⢄ ⢂ ⢁ ⡁ ⡈ ⡐ ⡠ ⢄ ⢂ ⢁
Path found, destination <a7f8b69872d97d16ab5bd64d2e90de3b> is 1 hop away
  via <a7f8b69872d97d16ab5bd64d2e90de3b>
  on TCPInterface[TCP Client to Node1/127.0.0.1:4242]
```

The spinning braille characters (⢄ ⢂ ⢁...) are a progress indicator while
the path is being resolved.

---

## 8. Connect to the Public Reticulum Network

### 8.1 The Dublin hub is down

The official Reticulum documentation references
`dublin.connect.reticulum.network:4965` as the public testnet entry point.

**As of 2026-03-01, this hostname does not resolve:**

```bash
$ nslookup dublin.connect.reticulum.network
*** cdns01.comcast.net can't find dublin.connect.reticulum.network: Non-existent domain
```

### 8.2 Community node list

The community maintains a list of public entry points at:
https://github.com/markqvist/Reticulum/wiki/Community-Node-List

We tested several nodes for DNS resolution and TCP connectivity:

| Node | Host | Port | DNS | TCP Connect |
|------|------|-----:|:---:|:-----------:|
| BetweenTheBorders Hub | `reticulum.betweentheborders.com` | 4242 | OK | **OK** |
| Beleth RNS Hub | `rns.beleth.net` | 4242 | OK | **OK** |
| acehoss | `rns.acehoss.net` | 4242 | OK | FAIL |
| Quad4 TCP Node 1 | `rns.quad4.io` | 4242 | OK | FAIL |

We chose the **BetweenTheBorders Hub** for this guide.

### 8.3 The connection in action

With the `[[BetweenTheBorders Hub]]` interface in Node1's config, `rnstatus`
shows:

```
 TCPInterface[BetweenTheBorders Hub/reticulum.betweentheborders.com:4242]
    Status    : Up
    Mode      : Full
    Rate      : 10.00 Mbps
    Traffic   : ↑838 B  0 bps
                ↓617 B  0 bps
```

Traffic is flowing in both directions. The ↓617 B is announce packets from
other nodes on the public network being received.

### 8.4 What "connected to the public network" means

Once Node1 connects to the public hub, **all three nodes** effectively join
the global Reticulum network:

- Node1 relays announce packets from the public network to Node2 and Node3
- Node2 and Node3 can resolve paths to any announced destination worldwide
- Any destination announced by Node2 or Node3 will propagate to the public
  network through Node1's transport

---

## 9. Install LXMF and Send Messages Between Nodes

### 9.1 Install NomadNet (includes LXMF)

```bash
$ pip install nomadnet
```

```
Successfully installed lxmf-0.9.4 nomadnet-0.9.8 qrcode-8.2 urwid-3.0.5 wcwidth-0.6.0
```

This installs:
- **LXMF 0.9.4** — the messaging protocol library
- **NomadNet 0.9.8** — a TUI (text UI) mesh messenger
- Supporting libraries (urwid for TUI, qrcode for identity sharing)

> **Note:** NomadNet is a full-screen terminal application. For our scripted
> demo we use the LXMF Python API directly, which allows non-interactive
> message sending and receiving.

### 9.2 Receiver script — runs on Node2

This script registers an LXMF delivery destination on Node2 and waits for
incoming messages.

**File: `scripts/lxmf_receiver.py`**

```python
#!/usr/bin/env python3
"""LXMF Receiver - listens for messages on Node2's Reticulum instance."""

import sys
import time
import os
import RNS
import LXMF

# Use node2's config directory
configdir = os.path.expanduser("~/reticulum-guide/node2")

def message_received(message):
    """Callback when a message arrives."""
    sender = RNS.prettyhexrep(message.source_hash)
    print(f"\n>>> MESSAGE RECEIVED <<<")
    print(f"  From:    {sender}")
    print(f"  Title:   {message.title_as_string()}")
    print(f"  Content: {message.content_as_string()}")
    print(f"  State:   {message.state}")
    print(f"  Method:  {'direct' if message.method == LXMF.LXMessage.DIRECT else 'propagation'}")
    sys.stdout.flush()

# Initialize Reticulum on node2's shared instance
reticulum = RNS.Reticulum(configdir=configdir)

# Create an LXMF router
router = LXMF.LXMRouter(storagepath=os.path.join(configdir, "lxmf_storage"))

# Generate or load identity for the receiver
identity_path = os.path.join(configdir, "receiver_identity")
if os.path.isfile(identity_path):
    identity = RNS.Identity.from_file(identity_path)
    print(f"Loaded existing receiver identity")
else:
    identity = RNS.Identity()
    identity.to_file(identity_path)
    print(f"Created new receiver identity")

# Register as an LXMF delivery destination
delivery = router.register_delivery_identity(identity, display_name="Node2 Receiver")
router.register_delivery_callback(message_received)

# Print address for sender to use
dest_hash = RNS.prettyhexrep(delivery.hash)
print(f"Receiver LXMF address: {dest_hash}")
print(f"Waiting for messages... (Ctrl+C to stop)")
sys.stdout.flush()

# Announce so the sender can discover us
router.announce(delivery.hash)

# Keep running
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nReceiver stopped.")
```

**How it works:**

1. Connects to Node2's running `rnsd` via the shared instance (port 37430)
2. Creates or loads a persistent Ed25519/X25519 identity
3. Registers an LXMF delivery destination (like an email inbox)
4. Sends an announce so other nodes can discover this destination
5. Prints the destination hash (the "address") and waits

### 9.3 Sender script — runs on Node3

This script sends an LXMF message from Node3 to a destination hash.

**File: `scripts/lxmf_sender.py`**

```python
#!/usr/bin/env python3
"""LXMF Sender - sends a message from Node3 to a destination hash."""

import sys
import time
import os
import RNS
import LXMF

# Use node3's config directory
configdir = os.path.expanduser("~/reticulum-guide/node3")

if len(sys.argv) < 2:
    print("Usage: python lxmf_sender.py <destination_hash>")
    print("  Get the destination hash from the receiver's output")
    sys.exit(1)

dest_hash_str = sys.argv[1].replace("<", "").replace(">", "").strip()

# Initialize Reticulum on node3's shared instance
reticulum = RNS.Reticulum(configdir=configdir)

# Create an LXMF router
router = LXMF.LXMRouter(storagepath=os.path.join(configdir, "lxmf_storage"))

# Generate or load sender identity
identity_path = os.path.join(configdir, "sender_identity")
if os.path.isfile(identity_path):
    identity = RNS.Identity.from_file(identity_path)
    print(f"Loaded existing sender identity")
else:
    identity = RNS.Identity()
    identity.to_file(identity_path)
    print(f"Created new sender identity")

# Register sender
source = router.register_delivery_identity(identity, display_name="Node3 Sender")

# Parse destination hash
dest_hash = bytes.fromhex(dest_hash_str)
print(f"Resolving path to <{dest_hash_str}>...")

# Request path to destination
if not RNS.Transport.has_path(dest_hash):
    RNS.Transport.request_path(dest_hash)
    print("Waiting for path resolution...")
    timeout = 15
    while not RNS.Transport.has_path(dest_hash) and timeout > 0:
        time.sleep(0.5)
        timeout -= 0.5

if RNS.Transport.has_path(dest_hash):
    # Get the destination identity
    dest_identity = RNS.Identity.recall(dest_hash)
    if dest_identity is None:
        print("Could not recall identity for destination. Waiting for announce...")
        timeout = 15
        while dest_identity is None and timeout > 0:
            time.sleep(0.5)
            dest_identity = RNS.Identity.recall(dest_hash)
            timeout -= 0.5

    if dest_identity:
        # Create the LXMF destination
        dest = RNS.Destination(
            dest_identity, RNS.Destination.OUT,
            RNS.Destination.SINGLE, "lxmf", "delivery"
        )

        # Create and send the message
        msg = LXMF.LXMessage(
            dest,
            source,
            "Hello from Node3! This is a test message sent via LXMF "
            "over our local Reticulum network.",
            title="Test Message"
        )
        msg.try_propagation_on_fail = False

        def delivery_callback(message):
            if message.state == LXMF.LXMessage.DELIVERED:
                print(f"Message DELIVERED successfully!")
            elif message.state == LXMF.LXMessage.FAILED:
                print(f"Message delivery FAILED")
            sys.stdout.flush()

        msg.register_delivery_callback(delivery_callback)

        print(f"Sending message to <{dest_hash_str}>...")
        router.handle_outbound(msg)

        # Wait for delivery
        timeout = 30
        while msg.state != LXMF.LXMessage.DELIVERED \
              and msg.state != LXMF.LXMessage.FAILED \
              and timeout > 0:
            time.sleep(0.5)
            timeout -= 0.5

        if msg.state == LXMF.LXMessage.DELIVERED:
            print("Message confirmed delivered!")
        elif msg.state == LXMF.LXMessage.FAILED:
            print(f"Message failed with state: {msg.state}")
        else:
            print(f"Timed out. State: {msg.state}")
    else:
        print("ERROR: Could not resolve destination identity.")
else:
    print("ERROR: Could not find path to destination.")

time.sleep(2)
print("Sender done.")
```

**How it works:**

1. Connects to Node3's running `rnsd` via the shared instance (port 37432)
2. Parses the receiver's destination hash from the command line
3. Requests a path to the destination (this propagates through Node1's
   transport)
4. Recalls the destination's public identity (needed for encryption)
5. Creates an LXMF message and hands it to the router
6. Waits for a delivery confirmation (the receiver sends back a receipt)

### 9.4 Running the message test

**Terminal 1 — start receiver on Node2:**

```bash
$ export PYTHONIOENCODING=utf-8
$ python ~/reticulum-guide/lxmf_receiver.py
```

```
Created new receiver identity
Receiver LXMF address: <443a952824ac97ba59d85570e178e9fd>
Waiting for messages... (Ctrl+C to stop)
```

Copy the address hash.

**Terminal 2 — send message from Node3:**

```bash
$ export PYTHONIOENCODING=utf-8
$ python ~/reticulum-guide/lxmf_sender.py 443a952824ac97ba59d85570e178e9fd
```

```
Created new sender identity
Resolving path to <443a952824ac97ba59d85570e178e9fd>...
Waiting for path resolution...
Sending message to <443a952824ac97ba59d85570e178e9fd>...
Message DELIVERED successfully!
Message confirmed delivered!
Sender done.
```

**Terminal 1 (receiver) now shows:**

```
>>> MESSAGE RECEIVED <<<
  From:    <d2a5fc26b05482a9f086370d30342686>
  Title:   Test Message
  Content: Hello from Node3! This is a test message sent via LXMF over our local Reticulum network.
  State:   0
  Method:  direct
```

### 9.5 What just happened — message flow

```
Node3 (sender)                   Node1 (transport)              Node2 (receiver)
     │                                │                              │
     │ 1. Path request for            │                              │
     │    <443a9528...>               │                              │
     ├───────────────────────────────►│                              │
     │                                │  2. Forward path request     │
     │                                ├─────────────────────────────►│
     │                                │                              │
     │                                │  3. Path response            │
     │                                │◄─────────────────────────────┤
     │  4. Path found (1 hop)         │                              │
     │◄───────────────────────────────┤                              │
     │                                │                              │
     │ 5. LXMF message (encrypted)   │                              │
     ├───────────────────────────────►│  6. Forward to destination   │
     │                                ├─────────────────────────────►│
     │                                │                              │
     │                                │  7. Delivery receipt         │
     │                                │◄─────────────────────────────┤
     │  8. Receipt forwarded          │                              │
     │◄───────────────────────────────┤                              │
     │                                │                              │
     ▼ "Message DELIVERED"            │                              ▼ "MESSAGE RECEIVED"
```

The message was end-to-end encrypted with X25519 key exchange and AES. Node1
(the transport node) forwarded it but **could not read the contents**.

---

## 10. Diagnostic & Management Tools — Full Reference

### 10.1 `rnsd` — Reticulum Daemon

The daemon that runs the Reticulum network stack. Must be running before any
other tool or program can use Reticulum.

```
Usage: rnsd [-h] [--config CONFIG] [-v] [-q] [-s] [-i] [--exampleconfig] [--version]

Options:
  --config CONFIG    Path to alternative Reticulum config directory
  -v, --verbose      Increase log verbosity
  -q, --quiet        Decrease log verbosity
  -s, --service      Log to file instead of console (for running as a service)
  -i, --interactive  Drop into interactive Python shell after init
  --exampleconfig    Print the full example config (472 lines) and exit
```

**Common patterns:**

```bash
# Start with a custom config directory (what we do in this guide)
rnsd --config ~/reticulum-guide/node1

# Run as a background service with file logging
rnsd -s &

# Generate the full example config for reference
rnsd --exampleconfig > example.conf
```

### 10.2 `rnstatus` — Network Status

The primary monitoring tool. Shows interface status, traffic, and system info.

```
Usage: rnstatus [-h] [--config CONFIG] [--version] [-a] [-A] [-l] [-t]
                [-s SORT] [-r] [-j] [-R hash] [-i path] [-w seconds]
                [-d] [-D] [-m] [-I seconds] [-v] [filter]

Options:
  -a, --all             Show ALL interfaces (including internal LocalInterface)
  -A, --announce-stats  Add announce frequency stats to each interface
  -l, --link-stats      Show link statistics
  -t, --totals          Show aggregate traffic totals
  -s SORT               Sort by: rate, traffic, rx, tx, rxs, txs, announces
  -r, --reverse         Reverse sort order
  -j, --json            Output as JSON (for scripting)
  -m, --monitor         Continuous monitoring mode (refreshes in-place)
  -I seconds            Refresh interval for monitor mode (default: 1)
  -R hash               Query a REMOTE transport instance
  -i path               Identity file for remote management auth
  filter                Only show interfaces matching this name filter
```

**Examples with output:**

```bash
# JSON output — useful for scripting/monitoring
$ rnstatus --config ~/reticulum-guide/node1 -j | python -m json.tool
{
    "interfaces": [...],
    "transport_id": "91e8c5eaaefbb5b0014a2b448f538349",
    "probe_responder": "a7f8b69872d97d16ab5bd64d2e90de3b",
    "rxb": 3874,
    "txb": 2927,
    "transport_uptime": 95.4
}

# Continuous monitor mode (like 'top' for Reticulum)
$ rnstatus --config ~/reticulum-guide/node1 -m -I 2
# (refreshes every 2 seconds, Ctrl+C to stop)

# Filter: only show interfaces with "TCP" in the name
$ rnstatus --config ~/reticulum-guide/node1 TCP
```

### 10.3 `rnpath` — Path Management

View and manage the routing table. Paths are learned from announces and path
requests.

```
Usage: rnpath [-h] [--config CONFIG] [-t] [-m hops] [-r] [-d] [-D]
              [-x] [-w seconds] [-R hash] [-i path] [-b] [-B] [-U]
              [--duration DURATION] [--reason REASON] [-j] [-v]
              [destination] [list_filter]

Options:
  -t, --table       Show all known paths
  -m hops           Filter path table by max hop count
  -r, --rates       Show announce rate info
  -d, --drop        Drop the path to a specific destination
  -D                Drop ALL queued announces
  -x, --drop-via    Drop all paths via a specific transport instance
  -b, --blackholed  List blackholed identities
  -B, --blackhole   Add an identity to the blackhole list
  -U, --unblackhole Remove from blackhole list
  -j, --json        JSON output
```

**Examples:**

```bash
# Show all known paths with verbose detail
$ rnpath --config ~/reticulum-guide/node1 -t -v

# Look up path to a specific destination (triggers path request if unknown)
$ rnpath --config ~/reticulum-guide/node2 a7f8b69872d97d16ab5bd64d2e90de3b

# Drop a stale path
$ rnpath --config ~/reticulum-guide/node1 -d <hash>

# Blackhole a spammy identity
$ rnpath --config ~/reticulum-guide/node1 -B <hash> --duration 24 --reason "spam"
```

### 10.4 `rnprobe` — Network Probe

Ping-like utility for testing transport node reachability. Sends probe
packets and measures round-trip time.

```
Usage: rnprobe [-h] [--config CONFIG] [-s SIZE] [-n PROBES] [-t seconds]
               [-w seconds] [--version] [-v]
               [full_name] [destination_hash]

Positional arguments:
  full_name          Full destination name (e.g., "rnstransport.probe")
  destination_hash   Hex hash of the destination

Options:
  -s SIZE            Payload size in bytes (default: 16)
  -n PROBES          Number of probes to send (default: 1)
  -t seconds         Timeout per probe
  -w seconds         Wait time between probes
  -v, --verbose      Show detailed output
```

**Requirements:**
- The target must be a **transport node** with `respond_to_probes = Yes`
- You must provide **both** the full name (`rnstransport.probe`) and the hash

**Gotcha:** Running `rnprobe <hash>` without the full name will just print
the help text and exit silently. Always include `"rnstransport.probe"` as
the first positional argument.

### 10.5 `rnid` — Identity & Encryption Utility

Swiss-army knife for Reticulum identities: generate, inspect, encrypt,
decrypt, sign, verify.

```
Usage: rnid [-h] [--config path] [-i identity] [-g file] [-m data]
            [-x] [-v] [-q] [-a aspects] [-H aspects] [-e file] [-d file]
            [-s path] [-V path] [-r file] [-w file] [-f] [-R] [-t seconds]
            [-p] [-P] [-b] [-B] [--version]

Options:
  -g file          Generate a new identity and save to file
  -i identity      Load identity from file or look up by hash
  -p               Print identity info (public key)
  -P               Print identity info INCLUDING private key
  -e file          Encrypt a file for this identity
  -d file          Decrypt a file with this identity
  -s path          Sign a file
  -V path          Verify a signature
  -r file          Input file path
  -w file          Output file path
  -f, --force      Overwrite existing output files
  -R, --request    Request unknown identities from the network
  -x, --export     Export identity in hex/base32/base64
  -b, --base64     Use base64 encoding
  -B, --base32     Use base32 encoding
```

**Example: generate, inspect, encrypt, decrypt**

```bash
# Generate a new identity
$ rnid -g ~/reticulum-guide/demo_identity
New identity <296929fd2c926ab74fb7afff08f82f2b> written to .../demo_identity

# Print the public key
$ rnid -i ~/reticulum-guide/demo_identity -p
Loaded Identity <296929fd2c926ab74fb7afff08f82f2b>
Public Key  : f79e6b9a39875df5...5d2438af7937615277...25227b3c
Private Key : Hidden

# Encrypt a file
$ echo "Secret message for Reticulum guide" > plaintext.txt
$ rnid -i ~/reticulum-guide/demo_identity -e plaintext.txt -w encrypted.bin -f
File plaintext.txt encrypted for <296929fd...> to encrypted.bin

# The encrypted file is 128 bytes (vs 35 bytes plaintext)
$ ls -la encrypted.bin
-rw-r--r-- 1 Andrew 197121 128 Mar  1 18:43 encrypted.bin

# Decrypt it back
$ rnid -i ~/reticulum-guide/demo_identity -d encrypted.bin -w decrypted.txt -f
File encrypted.bin decrypted with <296929fd...> to decrypted.txt

# Verify
$ cat decrypted.txt
Secret message for Reticulum guide
```

---

## 11. Troubleshooting

### 11.1 UnicodeEncodeError on Windows

**Symptom:**
```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2191'
  in position 16: character maps to <undefined>
```

**Cause:** Windows console uses cp1252 encoding. Reticulum uses Unicode
arrows (↑↓) and braille spinners (⢄⢂⢁⡁⡈⡐⡠).

**Fix:**
```bash
export PYTHONIOENCODING=utf-8
```

Add to `~/.bashrc` to make permanent. On PowerShell, use:
```powershell
$env:PYTHONIOENCODING = "utf-8"
```

### 11.2 Dublin testnet DNS failure

**Symptom:**
```
TCPInterface[Public Testnet Dublin/dublin.connect.reticulum.network:4965]
    Status    : Down
```

**Diagnosis:**
```bash
$ nslookup dublin.connect.reticulum.network
*** can't find dublin.connect.reticulum.network: Non-existent domain
```

**Fix:** The Dublin hub was not resolving as of 2026-03-01. Use community
nodes instead:

```ini
[[BetweenTheBorders Hub]]
  type = TCPClientInterface
  enabled = Yes
  target_host = reticulum.betweentheborders.com
  target_port = 4242
```

See the full list at:
https://github.com/markqvist/Reticulum/wiki/Community-Node-List

### 11.3 Config changes not taking effect after restart

**Symptom:** After editing `node1/config` and running `rnsd` again, the old
interfaces still appear in `rnstatus`.

**Cause:** The previous `rnsd` process is still running. Background shell
processes may detach and survive shell job control. The new `rnsd` process
either fails to bind (and exits silently) or binds to a different port.

**Diagnosis and fix:**

```bash
# Find what's listening on the shared instance port
$ netstat -ano | grep 37428
TCP    127.0.0.1:37428    0.0.0.0:0    LISTENING    8644

# Identify the process
$ powershell -Command "Get-Process -Id 8644 | Select ProcessName, Id"
ProcessName   Id
-----------   --
python      8644

# Kill it
$ powershell -Command "Stop-Process -Id 8644 -Force"

# Verify it's gone
$ netstat -ano | grep 37428
(no output)

# Now restart
$ rnsd --config ~/reticulum-guide/node1 &
```

> **Note:** `taskkill` from Git Bash often reports "Not found" even for valid
> PIDs. Use `powershell -Command "Stop-Process -Id <PID> -Force"` instead.

### 11.4 Port collision between nodes

**Symptom:** Second or third node fails to start. `rnstatus` for that node
reports connection errors or timeout.

**Cause:** Multiple nodes configured with the same `shared_instance_port`
or `instance_control_port`.

**Fix:** Each node needs a unique pair:

```ini
# node1                    # node2                    # node3
shared_instance_port=37428 shared_instance_port=37430 shared_instance_port=37432
instance_control_port=37429 instance_control_port=37431 instance_control_port=37433
```

### 11.5 `rnprobe` prints help instead of probing

**Symptom:** Running `rnprobe <hash>` just prints the usage message.

**Cause:** `rnprobe` requires **two** positional arguments: the full
destination name first, then the hash. With only one argument, argparse
interprets it as the name and waits for the hash, but since there are no
required args marked, it falls through to help.

**Fix:** Always provide both:

```bash
rnprobe "rnstransport.probe" "a7f8b69872d97d16ab5bd64d2e90de3b"
```

### 11.6 LXMF message stuck in "Waiting for path resolution"

**Symptom:** The sender prints "Waiting for path resolution..." and
eventually times out.

**Causes and fixes:**

1. **Receiver not running** — start `lxmf_receiver.py` first
2. **Receiver hasn't announced** — the receiver calls `router.announce()`
   on startup. If it was started recently, wait a few seconds.
3. **Wrong destination hash** — copy-paste the hash exactly from the
   receiver's output
4. **Transport node not running** — Node1 must be running with
   `enable_transport = Yes` for Node3 to reach Node2

### 11.7 Stopping all nodes cleanly

```bash
# Nuclear option: kill all Python processes
$ powershell -Command "Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force"

# Surgical: kill by shared instance port
$ netstat -ano | grep "37428.*LISTEN"  # find node1 PID
$ netstat -ano | grep "37430.*LISTEN"  # find node2 PID
$ netstat -ano | grep "37432.*LISTEN"  # find node3 PID
$ powershell -Command "Stop-Process -Id <pid1>,<pid2>,<pid3> -Force"
```

---

## 12. Files Created

```
reticulum-zero-budget-lab/
├── README.md                   # Repo overview, quick start
├── GUIDE.md                    # Full deployment guide (you are here)
├── LICENSE                     # MIT license
├── configs/
│   ├── node1/config            # Transport node + TCP server + public hub
│   ├── node2/config            # Leaf node, TCP client
│   └── node3/config            # Leaf node, TCP client
└── scripts/
    ├── lxmf_receiver.py        # LXMF receiver script (Node2)
    └── lxmf_sender.py          # LXMF sender script (Node3)
```

---

## 13. Quick-Start Cheat Sheet

Copy-paste this to bring up the full network in one go:

```bash
# ── Prerequisites ──
export PYTHONIOENCODING=utf-8

# ── Start the 3-node network ──
rnsd --config ~/reticulum-guide/node1 &
sleep 8  # allow time for public hub DNS + TCP connect
rnsd --config ~/reticulum-guide/node2 &
rnsd --config ~/reticulum-guide/node3 &
sleep 3

# ── Verify everything is up ──
echo "=== Node1 (transport + public gateway) ==="
rnstatus --config ~/reticulum-guide/node1

echo "=== Node2 (leaf) ==="
rnstatus --config ~/reticulum-guide/node2

echo "=== Node3 (leaf) ==="
rnstatus --config ~/reticulum-guide/node3

# ── Probe test (Node2 → Node1) ──
# Replace the hash below with YOUR probe responder hash from Node1's rnstatus output
rnprobe --config ~/reticulum-guide/node2 -v -t 10 -n 3 \
    "rnstransport.probe" "a7f8b69872d97d16ab5bd64d2e90de3b"

# ── View routing table ──
rnpath --config ~/reticulum-guide/node1 -t

# ── Send a message (needs two terminals) ──
# Terminal 1:
python ~/reticulum-guide/lxmf_receiver.py
# (note the LXMF address it prints)

# Terminal 2:
python ~/reticulum-guide/lxmf_sender.py <address_from_terminal_1>

# ── Stop everything ──
powershell -Command "Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force"
```

---

## Summary of Key Discoveries

| Finding | Detail |
|---------|--------|
| Windows requires unique ports | `shared_instance_port` / `instance_control_port` must differ per node |
| Unicode crash on Windows | `rnstatus` crashes with cp1252; fix: `PYTHONIOENCODING=utf-8` |
| Dublin hub DNS dead | `dublin.connect.reticulum.network` NXDOMAIN as of 2026-03-01 |
| Community nodes work | `reticulum.betweentheborders.com:4242` and `rns.beleth.net:4242` confirmed |
| `rnprobe` needs two args | Must pass `"rnstransport.probe"` AND the hash; hash alone prints help |
| `taskkill` unreliable in Git Bash | Use PowerShell `Stop-Process` instead |
| Localhost RTT ~1 ms | Expected for TCP loopback; 0% packet loss confirmed |
| LXMF direct delivery | Messages delivered in <1s between local nodes |
| End-to-end encryption | Transport node (Node1) cannot read message contents |
| Path expiry | Paths expire after 7 days by default |
