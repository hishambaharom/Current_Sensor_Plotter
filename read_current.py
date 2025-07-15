import serial
import struct
import binascii
import matplotlib.pyplot as plt
from collections import deque

def calculate_crc16(data):
    """
    Calculate the CRC16 checksum using the MODBUS-RTU polynomial.
    :param data: The input data as bytes.
    :return: The calculated CRC16 as a 2-byte integer.
    """
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF

def send_command(ser):
    """
    Send the command to request data from the device.
    :param ser: The serial object.
    """
    command = bytes([0x01, 0x03, 0x00, 0x56, 0x00, 0x01])
    crc = calculate_crc16(command)
    command += struct.pack('<H', crc)
    ser.write(command)
    print(f"Command sent: {command.hex()}")

def receive_data_with_crc(ser):
    """
    Receive data over UART, ensuring it starts with 0x01 and ends with a valid 2-byte CRC16.
    :param ser: The serial object.
    :return: Extracted 16-bit integer if valid, otherwise None.
    """
    try:
        while True:
            # Read data until we get the first byte as 0x01
            start_byte = ser.read(1)
            if not start_byte:
                continue

            if start_byte[0] == 0x01:
                # Read the remaining bytes (length depends on your protocol)
                # Assuming a fixed frame length for simplicity: 7 bytes after start
                frame = start_byte + ser.read(6)

                if len(frame) < 7:
                    continue  # Incomplete frame, ignore

                # Extract the 16-bit data (MSB and LSB)
                msb = frame[3]
                lsb = frame[4]
                data_value = (msb << 8) | lsb

                # Extract and validate the CRC16
                received_crc = struct.unpack('<H', frame[-2:])[0]
                calculated_crc = calculate_crc16(frame[:-2])

                if received_crc == calculated_crc:
                    print(f"Valid frame received: {frame.hex()}")
                    print(f"Extracted 16-bit data (MSB: {msb}, LSB: {lsb}): {data_value}")
                    return data_value
                else:
                    print(f"CRC mismatch. Received: {received_crc:04X}, Calculated: {calculated_crc:04X}")

    except serial.SerialException as e:
        print(f"Serial communication error: {e}")

if __name__ == "__main__":
    port_name = "/dev/ttyUSB0"  # Replace with your serial port
    baud_rate = 9600     # Replace with your baud rate

    window_size = 500  # Number of points to display in the rolling graph
    processed_data = deque(maxlen=window_size)

    plt.ion()
    fig, ax = plt.subplots()
    line, = ax.plot([], [], marker='o')
    ax.set_xlim(0, window_size - 1)
    ax.set_ylim(0, 2)  # Adjust y-axis limits as needed
    ax.set_title("Real-Time Processed Data Plot")
    ax.set_xlabel("Sample Time (s)")
    ax.set_ylabel("Processed Data Value Current (Amp)")

    print("Starting data collection. Press Ctrl+C to stop.")

    try:
        with serial.Serial(port_name, baud_rate, timeout=1) as ser:
            while True:
                send_command(ser)
                data_value = receive_data_with_crc(ser)
                if data_value is not None:
                    data_to_plot = data_value * 200 / 10000
                    processed_data.append(data_to_plot)

                    # Update the rolling plot
                    line.set_ydata(processed_data)
                    line.set_xdata(range(len(processed_data)))
                    ax.set_ylim(min(processed_data, default=0), max(processed_data, default=1) + 0.1)
                    plt.draw()
                    plt.pause(0.1)

    except KeyboardInterrupt:
        print("Data collection stopped.")
        plt.show()

    if len(processed_data) > 0:
        print(f"Collected processed data points: {list(processed_data)}")
    else:
        print("No data collected.")

