
import serial
import struct
import time

# USB configuration
PORT = "COM5"
BAUD_RATE = 115200

# STIMRIG protocol configuration
SYNC = bytes.fromhex("A5 5A 5A A5")
FRAMES_PER_PACKET = 16
CHANNEL_COUNT = 16
PACKET_SIZE = 8 + FRAMES_PER_PACKET * CHANNEL_COUNT * 2

# Statistics
packets_received = 0
missing_frames = 0
last_seq = None
start_time = time.monotonic()

with serial.Serial(PORT, BAUD_RATE, timeout=2) as ser:
    print(f"Connected to {PORT}")
    print(f"Packet size: {PACKET_SIZE} bytes")
    print("Waiting for STIMRIG binary packets...\n")

    buffer = bytearray()

    while True:
        # Read incoming USB CDC bytes
        buffer.extend(ser.read(1024))

        while True:
            # Find start of packet
            start = buffer.find(SYNC)

            if start == -1:
                # Preserve possible partial sync marker
                if len(buffer) > len(SYNC) - 1:
                    del buffer[:-(len(SYNC) - 1)]
                break

            # Remove bytes before sync
            if start > 0:
                del buffer[:start]

            # Wait until complete packet arrives
            if len(buffer) < PACKET_SIZE:
                break

            packet = bytes(buffer[:PACKET_SIZE])
            del buffer[:PACKET_SIZE]

            # Decode first sample-frame index
            sequence = struct.unpack_from("<I", packet, 4)[0]

            # Decode 16 frames x 16 channels
            samples = struct.unpack_from(
                f"<{FRAMES_PER_PACKET * CHANNEL_COUNT}H",
                packet,
                8
            )

            frames = [
                samples[i * CHANNEL_COUNT:(i + 1) * CHANNEL_COUNT]
                for i in range(FRAMES_PER_PACKET)
            ]

            # Detect missing sample frames
            if last_seq is not None:
                expected = (last_seq + FRAMES_PER_PACKET) & 0xFFFFFFFF

                if sequence != expected:
                    gap = (sequence - expected) & 0xFFFFFFFF
                    missing_frames += gap

                    print(
                        f"Sequence gap: expected {expected}, "
                        f"received {sequence}"
                    )

            last_seq = sequence
            packets_received += 1

            # Print statistics approximately once per second
            elapsed = time.monotonic() - start_time

            if elapsed >= 1.0:
                packet_rate = packets_received / elapsed
                throughput_kb = (
                    packets_received * PACKET_SIZE / elapsed / 1000
                )
                frame_rate = (
                    packets_received * FRAMES_PER_PACKET / elapsed
                )

                print(
                    f"Rate: {packet_rate:.1f} packets/s | "
                    f"{frame_rate:.1f} frames/s | "
                    f"{throughput_kb:.2f} KB/s | "
                    f"Missing frames: {missing_frames}"
                )

                packets_received = 0
                start_time = time.monotonic()

            # Uncomment to inspect the first frame of each packet:
            #print(f"SEQ {sequence}: {frames[0]}")

# Stop with Ctrl+C
