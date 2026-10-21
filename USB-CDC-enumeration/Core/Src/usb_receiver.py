
import serial
import struct

PORT = "COM5"        # Replace with your STM32 User USB port
BAUD_RATE = 115200
SYNC = bytes.fromhex("A5 5A 5A A5")
PACKET_SIZE = 40

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
                    print(f"Sequence gap: expected {expected}, got {sequence}")

            last_seq = sequence

            print(f"SEQ {sequence}: {channels}")
