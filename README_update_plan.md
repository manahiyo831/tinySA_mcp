# Plan for Updating README.md: Architecture and Threading Model

## 1. Current README Issues

- No explanation of how the MCP server and Tkinter (GUI) run concurrently, or the restriction that Tkinter must run in the main thread.
- No mention of the threading design or the use of a queue for safe communication between threads.
- No documentation of how the MCP server and GUI coordinate startup and shutdown.

---

## 2. Key Findings from Code Analysis

### Architecture Overview

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

- **Tkinter (GUI) runs only in the main thread**  
  The main thread initializes the Tkinter root window and GUI, and runs mainloop().
- **MCP server runs in a background thread**  
  The MCP server is started using `threading.Thread`, allowing it to operate concurrently with the GUI.
- **Thread-safe communication via queue.Queue**  
  Log messages from the MCP server or other threads are put into a queue, and the GUI polls this queue using `root.after` for safe updates.
- **Graceful shutdown**  
  When the MCP server stops, it schedules the GUI to close using `root.after(0, root.destroy)`.

---

## 3. Proposed README Additions

### New Section: Architecture and Threading Model

This project uses both a Tkinter-based GUI and an MCP server. Due to Tkinter's requirement to run in the main thread, the following design is used:

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

---

## 4. Next Actions

1. Insert the new "Architecture and Threading Model" section after the "Overview" section in README.md.
2. Optionally add a brief note in "Troubleshooting" about Tkinter/main thread requirements.