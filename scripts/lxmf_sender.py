#!/usr/bin/env python3
"""
LXMF Sender — sends an encrypted message to an LXMF destination.

Part of the Reticulum Zero-Budget Lab.
https://github.com/AndrewHeron/reticulum-zero-budget-lab

Usage:
    python lxmf_sender.py <destination_hash> [--config PATH] [--message TEXT] [--title TEXT]

    destination_hash   The receiver's LXMF address (from lxmf_receiver.py output)
    --config PATH      Path to Reticulum config directory (default: ~/reticulum-guide/node3)
    --message TEXT     Message body (default: "Hello from the Reticulum Zero-Budget Lab!")
    --title TEXT       Message title (default: "Test Message")
"""

import argparse
import sys
import time
import os
import RNS
import LXMF


def main():
    parser = argparse.ArgumentParser(description="LXMF Sender for Reticulum Zero-Budget Lab")
    parser.add_argument(
        "destination",
        help="Receiver's LXMF destination hash (hex string)",
    )
    parser.add_argument(
        "--config",
        default=os.path.expanduser("~/reticulum-guide/node3"),
        help="Path to Reticulum config directory (default: ~/reticulum-guide/node3)",
    )
    parser.add_argument(
        "--message",
        default="Hello from the Reticulum Zero-Budget Lab! This is an end-to-end encrypted message sent via LXMF.",
        help="Message body",
    )
    parser.add_argument(
        "--title",
        default="Test Message",
        help="Message title",
    )
    args = parser.parse_args()

    configdir = args.config
    dest_hash_str = args.destination.replace("<", "").replace(">", "").strip()

    # Initialize Reticulum on the node's shared instance
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

    if not RNS.Transport.has_path(dest_hash):
        print("ERROR: Could not find path to destination.")
        print("       Make sure the receiver is running and has announced.")
        sys.exit(1)

    # Get the destination identity
    dest_identity = RNS.Identity.recall(dest_hash)
    if dest_identity is None:
        print("Waiting for identity resolution...")
        timeout = 15
        while dest_identity is None and timeout > 0:
            time.sleep(0.5)
            dest_identity = RNS.Identity.recall(dest_hash)
            timeout -= 0.5

    if dest_identity is None:
        print("ERROR: Could not resolve destination identity.")
        print("       The receiver may not have announced recently.")
        sys.exit(1)

    # Create the LXMF destination
    dest = RNS.Destination(
        dest_identity,
        RNS.Destination.OUT,
        RNS.Destination.SINGLE,
        "lxmf",
        "delivery",
    )

    # Create and send the message
    msg = LXMF.LXMessage(dest, source, args.message, title=args.title)
    msg.try_propagation_on_fail = False

    delivered = False

    def delivery_callback(message):
        nonlocal delivered
        if message.state == LXMF.LXMessage.DELIVERED:
            print(f"Message DELIVERED successfully!")
            delivered = True
        elif message.state == LXMF.LXMessage.FAILED:
            print(f"Message delivery FAILED.")
        sys.stdout.flush()

    msg.register_delivery_callback(delivery_callback)

    print(f"Sending message to <{dest_hash_str}>...")
    router.handle_outbound(msg)

    # Wait for delivery
    timeout = 30
    while not delivered and msg.state != LXMF.LXMessage.FAILED and timeout > 0:
        time.sleep(0.5)
        timeout -= 0.5

    if delivered:
        print("Message confirmed delivered!")
    elif msg.state == LXMF.LXMessage.FAILED:
        print(f"Message failed.")
        sys.exit(1)
    else:
        print(f"Timed out waiting for delivery confirmation.")
        sys.exit(1)

    time.sleep(1)


if __name__ == "__main__":
    main()
