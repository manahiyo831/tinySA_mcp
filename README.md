# tinysa-mcp

MCP server for operating TinySA through serial port

## Overview
This project is an MCP server designed to operate a TinySA device via a serial port. It leverages Python libraries such as pyserial, httpx, numpy, Pillow, and FastMCP to provide a tool-based interface for connecting to the device, executing commands, and retrieving device version information.

## Features
- Automatic detection and connection to a TinySA device.
- Send commands and retrieve responses from the device.
- Retrieve firmware and hardware version information.
- Disconnect the device as needed.
- Exposes MCP tools for integration with other systems.
- Supports image capture from the device screen, and optional file saving with timestamps.
- Basic troubleshooting messages for connection issues.

## Installation
Ensure Python >=3.13 is installed. Install project dependencies using Hatch:
```
hatch run build
```
or directly install the required packages:
```
pip install httpx mcp[cli]>=1.4.1 pyserial numpy Pillow
```

## Configuration
The project configuration is defined in `pyproject.toml`. Adjust serial port settings and baud rate in your environment if needed. You can override these settings using environment variables if required.

## Running the Server
To run the MCP server, execute:
```
python tinySA_Operator.py
```
This will start the MCP server using the stdio transport.

## MCP Tools
The following MCP tools are available:
- **get_version**: Retrieve version information from the TinySA device.
- **execute_command**: Send a command to the TinySA device and get the response.
- **connect**: Connect to the TinySA device on a specified port.
- **disconnect**: Disconnect the TinySA device.
- **get_device_info**: Retrieve detailed information about the connected device.
- **capture_image**: Capture the TinySA screen image and optionally save it to a file with a timestamp.

## Usage Example
Invoke the MCP tools using an MCP client. For example, to get the device version:
```
mcp call get_version --args '{"port": "COM3"}'
```

## Troubleshooting
- **Connection Issues:** Ensure the specified serial port is correct and that your user has appropriate permissions.
- **Command Failures:** Check the MCP server logs (if available) for error messages.
- **Image Capture:** Verify that the device returns sufficient data (307200 bytes) during image capture.
- Refer to the [Model Context Protocol documentation](https://modelcontextprotocol.io/docs) for more information on MCP integration.

## Materials
Refer to the `material` directory for additional documentation, including the TinySA user manual and USB interface details.

## License
This project is licensed under the MIT License.