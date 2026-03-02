#!/usr/bin/env python3
"""
LXMF Receiver — listens for messages on a Reticulum node.

Part of the Reticulum Zero-Budget Lab.
https://github.com/AndrewHeron/reticulum-zero-budget-lab

Usage:
    python lxmf_receiver.py [--config PATH]

    --config PATH   Path to Reticulum config directory (default: ~/reticulum-guide/node2)

The receiver will:
  1. Connect to the running rnsd shared instance
  2. Create or load a persistent identity
  3. Register an LXMF delivery destination
  4. Announce itself so senders can discover it
  5. Print incoming messages to stdout
"""

import argparse
import sys
import time
import os
import RNS
import LXMF


def message_received(message):
    """Callback fired when an LXMF message arrives."""
    sender = RNS.prettyhexrep(message.source_hash)
    method = "direct" if message.method == LXMF.LXMessage.DIRECT else "propagation"
    print(f"\n{'='*60}")
    print(f"  MESSAGE RECEIVED")
    print(f"{'='*60}")
    print(f"  From:    {sender}")
    print(f"  Title:   {message.title_as_string()}")
    print(f"  Content: {message.content_as_string()}")
    print(f"  Method:  {method}")
    print(f"{'='*60}")
    sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser(description="LXMF Receiver for Reticulum Zero-Budget Lab")
    parser.add_argument(
        "--config",
        default=os.path.expanduser("~/reticulum-guide/node2"),
        help="Path to Reticulum config directory (default: ~/reticulum-guide/node2)",
    )
    args = parser.parse_args()
    configdir = args.config

    # Initialize Reticulum on the node's shared instance
    reticulum = RNS.Reticulum(configdir=configdir)

    # Create an LXMF router
    router = LXMF.LXMRouter(storagepath=os.path.join(configdir, "lxmf_storage"))

    # Generate or load a persistent identity
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
    print(f"")
    print(f"  Receiver LXMF address: {dest_hash}")
    print(f"  Waiting for messages... (Ctrl+C to stop)")
    print(f"")
    sys.stdout.flush()

    # Announce so the sender can discover us
    router.announce(delivery.hash)

    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nReceiver stopped.")


if __name__ == "__main__":
    main()
