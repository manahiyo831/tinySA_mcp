# tinysa-mcp

MCP server for operating TinySA through serial port

**Sorry, I'm currently experimenting and cannot guarantee that it will work properly.**

## Overview
This project is an MCP server designed to operate a TinySA device via a serial port. It leverages Python libraries such as pyserial, httpx, numpy, Pillow, and FastMCP to provide a tool-based interface for connecting to the device, executing commands, and retrieving device version information.

## Features
- Send commands and retrieve responses from the device.
- Retrieve firmware and hardware version information.
- Exposes MCP tools for integration with other systems.
- Supports image capture from the device screen, and optional file saving with timestamps.

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
mcp call get_version --args '{"port": "COM4"}'
```

## Troubleshooting
- **Connection Issues:** Ensure the specified serial port is correct and that your user has appropriate permissions.
- **Command Failures:** Check the MCP server logs (if available) for error messages.
- **Image Capture:** Verify that the device returns sufficient data (307200 bytes) during image capture.
- Refer to the [Model Context Protocol documentation](https://modelcontextprotocol.io/docs) for more information on MCP integration.

## Materials
Refer to the `material` directory for additional documentation, it will be good to add the file "USB interface.txt" as a AI knowledge.

## License
This project is licensed under the MIT License.