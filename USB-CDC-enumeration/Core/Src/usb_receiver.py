
import serial
import struct
import time

PORT = "COM5"        # Replace with your STM32 User USB port
BAUD_RATE = 115200
SYNC = bytes.fromhex("A5 5A 5A A5")
PACKET_SIZE = 40

start_time = time.monotonic()
packets_received = 0

missing_packets = 0 # Count of missing packets

with serial.Serial(PORT, BAUD_RATE, timeout=2) as ser:
    print(f"Connected to {PORT}")
    print("Waiting for STIMRIG binary packets...\n")

    buffer = bytearray()
    last_seq = None

    while True:
        buffer.extend(ser.read(256))

        while True:
            start = buffer.find(SYNC)

            if start == -1:
                # Keep the final 3 bytes in case SYNC is split
                # across two serial reads.
                if len(buffer) > 3:
                    del buffer[:-3]
                break

            # Discard anything preceding the sync marker.
            if start > 0:
                del buffer[:start]

            # Wait until the entire 40-byte frame is present.
            if len(buffer) < PACKET_SIZE:
                break

            packet = bytes(buffer[:PACKET_SIZE])
            del buffer[:PACKET_SIZE]

            # Bytes 4-7: unsigned 32-bit sequence number
            sequence = struct.unpack_from("<I", packet, 4)[0]

            # Bytes 8-39: sixteen unsigned 16-bit samples
            channels = struct.unpack_from("<16H", packet, 8)

            if last_seq is not None:
                expected = (last_seq + 1) & 0xFFFFFFFF

                if sequence != expected:
                    missing = (sequence - expected) & 0xFFFFFFFF
                    missing_packets += missing
                    print(f"Sequence gap! Missing {missing} frames")

            last_seq = sequence

            packets_received += 1

            elapsed = time.monotonic() - start_time

            if elapsed >= 1.0:
                print(
                    f"Rate: {packets_received / elapsed:.1f} packets/s | "
                    f"{packets_received * 40 / elapsed / 1000:.2f} KB/s"
                    f" | Missing packets: {missing_packets}"
                )

                packets_received = 0
                start_time = time.monotonic()

            # print(f"SEQ {sequence}: {channels}")
