# Reticulum Zero-Budget Lab

**Deploy a 3-node encrypted mesh network in 30 minutes. No hardware. No budget. Just `pip install`.**

---

## What Is This?

A step-by-step lab guide for setting up a working [Reticulum](https://reticulum.network/) mesh network on a single machine using only TCP/IP. You'll build a 3-node topology, connect it to the live public Reticulum network, and send end-to-end encrypted messages between nodes — all without buying any hardware.

```
+-------------------------------------------+
|         Public Reticulum Network           |
+---------------------+---------------------+
                      |
           +----------+----------+
           |       Node 1        |
           |  Transport + Server |
           +-----+----------+---+
                 |          |
          +------+--+  +---+------+
          | Node 2  |  |  Node 3  |
          |  Leaf   |  |   Leaf   |
          +---------+  +----------+
```

## Who Is This For?

- Anyone curious about Reticulum who wants to try it without buying an RNode or radio
- Network engineers evaluating Reticulum for off-grid / resilient comms
- Developers building on the Reticulum stack (LXMF, NomadNet, Sideband)
- Homelab enthusiasts who want an encrypted mesh in their toolkit

## Prerequisites

- **Python 3.8+** (tested on 3.12)
- **pip**
- A terminal (Git Bash, PowerShell, WSL, or any Linux/macOS shell)
- ~10 minutes of patience

## Quick Start

**1. Install:**

```bash
pip install rns nomadnet
```

**2. Copy the configs into place:**

```bash
mkdir -p ~/reticulum-guide/node1 ~/reticulum-guide/node2 ~/reticulum-guide/node3
cp configs/node1/config ~/reticulum-guide/node1/config
cp configs/node2/config ~/reticulum-guide/node2/config
cp configs/node3/config ~/reticulum-guide/node3/config
```

**3. Start the network:**

```bash
export PYTHONIOENCODING=utf-8   # Required on Windows
rnsd --config ~/reticulum-guide/node1 &
sleep 8
rnsd --config ~/reticulum-guide/node2 &
rnsd --config ~/reticulum-guide/node3 &
sleep 3
rnstatus --config ~/reticulum-guide/node1
```

**4. Follow the full guide:** **[GUIDE.md](GUIDE.md)**

The guide walks through every step with full terminal output so you know exactly what to expect.

## What You'll Learn

- How Reticulum's identity-based addressing works (no IP addresses)
- How to configure TCP server/client interfaces
- How transport routing connects leaf nodes through a hub
- How to connect a local mesh to the live public Reticulum network
- How to send end-to-end encrypted LXMF messages programmatically
- How to use `rnstatus`, `rnpath`, `rnprobe`, and `rnid` for diagnostics
- Windows-specific gotchas (port isolation, UTF-8 encoding, process management)

## Repo Structure

```
reticulum-zero-budget-lab/
├── README.md                   # You are here
├── GUIDE.md                    # Full deployment guide (1500+ lines)
├── LICENSE                     # MIT
├── configs/
│   ├── node1/config            # Transport node + TCP server + public hub
│   ├── node2/config            # Leaf node (message receiver)
│   └── node3/config            # Leaf node (message sender)
└── scripts/
    ├── lxmf_receiver.py        # LXMF message receiver
    └── lxmf_sender.py          # LXMF message sender
```

## Key Findings

| Discovery | Detail |
|-----------|--------|
| Windows needs unique ports | `shared_instance_port` must differ per node (no domain sockets) |
| Dublin hub DNS is dead | `dublin.connect.reticulum.network` returns NXDOMAIN — use community nodes |
| `rnprobe` needs two args | Must pass `"rnstransport.probe"` AND the hash; hash alone silently fails |
| Localhost mesh RTT | ~1 ms round-trip, 0% packet loss |
| LXMF delivery | End-to-end encrypted, confirmed delivered in <1 second locally |

## Related Projects

- [Reticulum](https://github.com/markqvist/Reticulum) — the networking stack
- [LXMF](https://github.com/markqvist/lxmf) — the messaging protocol
- [NomadNet](https://github.com/markqvist/NomadNet) — TUI mesh messenger
- [Sideband](https://github.com/markqvist/Sideband) — mobile/desktop messenger
- [Community Node List](https://github.com/markqvist/Reticulum/wiki/Community-Node-List) — public entry points

## Author

**Andrew Heron** — [Heron Networks LLC](https://heronnetworks.com)

## License

[MIT](LICENSE)
