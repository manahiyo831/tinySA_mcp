# tinysa-mcp

MCP server for operating TinySA through serial port

**Sorry, I'm currently experimenting and cannot guarantee that it will work properly.**

## Overview
This project is an MCP server designed to operate a TinySA device via a serial port. It leverages Python libraries such as pyserial, httpx, numpy, Pillow, and FastMCP to provide a tool-based interface for connecting to the device, executing commands, and retrieving device version information.

## Architecture and Threading Model

This project uses both a Tkinter-based GUI and an MCP server. Due to Tkinter's requirement to run in the main thread, the following design is used:

```mermaid
flowchart TD
    subgraph MainThread
        A[main()] --> B[tk.Tk() & TinySALogMonitor]
        B --> C[root.mainloop()]
    end
    subgraph MCPThread
        D[run_mcp_server(mcp_server)]
        D --> E[mcp_server.run()]
    end
    E -- log_callback --> F[log_monitor.log_queue]
    F -- root.afterで定期ポーリング --> B
    D -- サーバー終了時 --> G[root.after(0, root.destroy)]
```

- **Tkinter GUI runs in the main thread**:  
  The main thread initializes the Tkinter root window and starts the main event loop. All GUI operations are performed in this thread.

- **MCP server runs in a background thread**:  
  The MCP server is started in a separate thread using Python's `threading.Thread`. This allows the server to handle requests concurrently with the GUI.

- **Thread-safe communication via queue**:  
  Log messages and other data from the MCP server (or other background threads) are sent to the GUI using a `queue.Queue`. The GUI periodically polls this queue using `root.after` to update the display safely.

- **Graceful shutdown**:  
  When the MCP server stops, it schedules the GUI to close using `root.after(0, root.destroy)`, ensuring all Tkinter operations remain in the main thread.

#### Example (main function):

```python
def main():
    root = tk.Tk()
    log_monitor = TinySALogMonitor(root)
    mcp_server = create_mcp_server(log_monitor.add_log)
    mcp_thread = threading.Thread(target=run_mcp_server, args=(mcp_server,), daemon=True)
    mcp_thread.start()
    root.mainloop()
```

#### Notes

- **Do not access Tkinter objects from background threads.**  
  Always use the provided queue and `root.after` for thread-safe communication.
- **This design ensures both the MCP server and the GUI can run concurrently without violating Tkinter's threading requirements.**

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