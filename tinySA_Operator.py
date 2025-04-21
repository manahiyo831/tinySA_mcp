import serial
import time
from typing import Dict, Any, Optional, List, Union
import base64
import os
import threading
import queue
from mcp.server.fastmcp import FastMCP, Image
import mcp.types as types
import struct
import numpy as np
import datetime
from PIL import Image as PILImage
import io
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog

# オリジナルのTinySASerialクラスを拡張してログ機能を追加
class TinySASerial:
    """Class to handle serial communication with TinySA device."""
    
    def __init__(self, port: Optional[str] = None, baudrate: int = 9600, log_callback=None):
        self.port = port
        self.baudrate = baudrate
        self.timeout = 3
        self.serial_conn: Optional[serial.Serial] = None
        self.connected = False
        self.log_callback = log_callback  # ログ表示用コールバック関数
    
    def log(self, message, level="INFO"):
        """ログメッセージを記録する"""
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        log_msg = f"[{timestamp}] [{level}] {message}"
        if self.log_callback:
            self.log_callback(log_msg)
        else:
            print(log_msg)
    
    def connect(self, port: Optional[str] = None) -> bool:
        """Connect to TinySA device. Port is required if not already set."""
        if port:
            self.port = port
        if not self.port:
            self.log("Error: Port parameter is required for connection.", "ERROR")
            return False
        try:
            self.log(f"Connecting to TinySA on port {self.port}...")
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=self.timeout
            )
            self.connected = True
            self.log(f"Successfully connected to TinySA on port {self.port}", "SUCCESS")
            return True
        except (serial.SerialException, OSError) as e:
            self.log(f"Error connecting to TinySA: {e}", "ERROR")
            self.connected = False
            return False
    
    def disconnect(self) -> None:
        """Disconnect from TinySA device."""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            self.log(f"Disconnected from TinySA on port {self.port}")
        self.connected = False

    def get_image_data(self) -> bytearray:
        """Get screen data from TinySA device."""
        if self.serial_conn and self.serial_conn.is_open:
            # Clear any pending data
            self.serial_conn.reset_input_buffer()
            command = "capture\r"
            self.log(f"TX: {command.strip()}")
            self.serial_conn.write(command.encode('utf-8'))
            self.log(f"Reading image data...")
            data = self.serial_conn.read(307200)
            self.log(f"RX: Image data received ({len(data)} bytes)")
            ans = bytearray(307200)
            ans[0:len(data)] = data            
            return ans
        else:
            self.log("Not connected to TinySA device. Please execute connect command.", "ERROR")
            raise Exception("Not connected to TinySA device. Please execute connect command.")

    def send_command(self, command: str, wait_time: float = 0.1) -> str:
        """Send command to TinySA and return response. """
        if not self.connected or not self.serial_conn:
            self.log("Not connected to TinySA device. Please execute connect command.", "ERROR")
            raise Exception("Not connected to TinySA device. Please execute connect command.")
        
        try:
            # Clear any pending data
            self.serial_conn.reset_input_buffer()
            
            # Send command with newline
            cmd = command.strip() + "\r\n"
            self.log(f"TX: {command.strip()}")
            self.serial_conn.write(cmd.encode('utf-8'))
            
            # Wait for device to process command
            time.sleep(wait_time)
            
            # Read response
            response = ""
            while self.serial_conn.in_waiting:
                chunk = self.serial_conn.read(self.serial_conn.in_waiting).decode('utf-8', errors='replace')
                response += chunk
                self.log(f"RX: {chunk.strip()}")
                time.sleep(0.1)  # Small delay to ensure all data is received
            
            return response.strip()
        except (serial.SerialException, OSError) as e:
            self.log(f"Error communicating with TinySA: {e}", "ERROR")
            raise Exception(f"Error communicating with TinySA: {e}")
    
    def get_version(self) -> Dict[str, str]:
        """Get TinySA version information."""
        try:
            # Send version command
            self.log("Getting TinySA version information...")
            response = self.send_command("version")
            
            # Parse version information
            version_info = {
                "raw_response": response
            }
            
            # Split the response into lines
            lines = response.strip().split('\n')
            
            # Process version information
            if lines and len(lines) >= 2:
                version_info["firmware"] = lines[1].strip()
            if lines and len(lines) >= 3:
                version_info["hardware"] = lines[2].strip()
            
            return version_info
        except Exception as e:
            self.log(f"Error getting TinySA version: {e}", "ERROR")
            raise Exception(f"Error getting TinySA version: {e}")


# GUIクラス - シリアル通信のログ表示のみ
class TinySALogMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("TinySA Communication Log Monitor")
        self.root.geometry("800x600")
        
        # ログキュー
        self.log_queue = queue.Queue()
        
        # ウインドウ表示状態
        self.window_visible = True

        # UIのセットアップ
        self.setup_ui()
        
        # ログの自動更新タイマー
        self.root.after(100, self.update_log_from_queue)
    
    def setup_ui(self):
        # メインフレームの作成
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # ステータスフレーム
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(status_frame, text="MCP Server Status:").pack(side=tk.LEFT, padx=5)
        self.status_label = ttk.Label(status_frame, text="Running", foreground="green")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        # タイムスタンプ
        self.timestamp_label = ttk.Label(status_frame, text="")
        self.timestamp_label.pack(side=tk.RIGHT, padx=5)
        self.update_timestamp()
        
        # ログ表示フレーム
        self.log_frame = ttk.LabelFrame(main_frame, text="Serial Communication Log")
        self.log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # ログテキストボックス
        self.log_text = scrolledtext.ScrolledText(self.log_frame, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # コントロールフレーム
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=5)
        
        # クリアボタン
        self.clear_log_button = ttk.Button(control_frame, text="Clear Log", command=self.clear_log)
        self.clear_log_button.pack(side=tk.LEFT, padx=5)
        
        # 保存ボタン
        self.save_log_button = ttk.Button(control_frame, text="Save Log", command=self.save_log)
        self.save_log_button.pack(side=tk.LEFT, padx=5)
        
        # フィルターフレーム
        filter_frame = ttk.LabelFrame(main_frame, text="Log Filter")
        filter_frame.pack(fill=tk.X, pady=5)
        
        # 送信フィルター
        self.show_tx = tk.BooleanVar(value=True)
        ttk.Checkbutton(filter_frame, text="Show TX", variable=self.show_tx, command=self.apply_filters).pack(side=tk.LEFT, padx=20)
        
        # 受信フィルター
        self.show_rx = tk.BooleanVar(value=True)
        ttk.Checkbutton(filter_frame, text="Show RX", variable=self.show_rx, command=self.apply_filters).pack(side=tk.LEFT, padx=20)
        
        # エラーフィルター
        self.show_errors = tk.BooleanVar(value=True)
        ttk.Checkbutton(filter_frame, text="Show Errors", variable=self.show_errors, command=self.apply_filters).pack(side=tk.LEFT, padx=20)
        
        # その他フィルター
        self.show_other = tk.BooleanVar(value=True)
        ttk.Checkbutton(filter_frame, text="Show Other", variable=self.show_other, command=self.apply_filters).pack(side=tk.LEFT, padx=20)
    
    def update_timestamp(self):
        """タイムスタンプを更新"""
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.timestamp_label.config(text=f"Last update: {current_time}")
        self.root.after(1000, self.update_timestamp)  # 1秒ごとに更新
    
    def add_log(self, message):
        """ログキューにメッセージを追加"""
        self.log_queue.put(message)
    
    def update_log_from_queue(self):
        """キューからログメッセージを取得して表示"""
        while not self.log_queue.empty():
            message = self.log_queue.get()
            
            # メッセージタイプに応じた色を設定
            if "TX:" in message:
                tag = "tx"
                color = "blue"
            elif "RX:" in message:
                tag = "rx"
                color = "green"
            elif "ERROR" in message:
                tag = "error"
                color = "red"
            else:
                tag = "other"
                color = "black"
            
            # メッセージを追加
            self.log_text.insert(tk.END, message + "\n", tag)
            self.log_text.tag_config(tag, foreground=color)
            self.log_text.see(tk.END)  # 常に最新のログを表示
        
        # 再度タイマーを設定
        self.root.after(100, self.update_log_from_queue)
    
    def apply_filters(self):
        """フィルター設定を適用"""
        # 全てのタグを非表示にする
        for tag, show_var in [("tx", self.show_tx), ("rx", self.show_rx), 
                              ("error", self.show_errors), ("other", self.show_other)]:
            if show_var.get():
                self.log_text.tag_config(tag, elide=False)
            else:
                self.log_text.tag_config(tag, elide=True)
    
    def clear_log(self):
        """ログをクリア"""
        self.log_text.delete(1.0, tk.END)
    
    def save_log(self):
        """ログをファイルに保存"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.log_text.get(1.0, tk.END))
            self.add_log(f"[INFO] Log saved to {file_path}")


    def set_log_visible(self, visible: bool):
        """Show or hide the entire log window."""
        if visible and not self.window_visible:
            self.root.deiconify()
            self.window_visible = True
        elif not visible and self.window_visible:
            self.root.withdraw()
            self.window_visible = False

# グローバル変数
tinySA = None
log_monitor = None

# MCPサーバー関数の定義
def create_mcp_server(log_callback):
    global tinySA
    
    # TinySAシリアルインスタンスを初期化
    tinySA = TinySASerial(log_callback=log_callback)
    
    # MCPサーバーの初期化
    mcp = FastMCP(
        name="tinySA-operator",
        version="0.1.0",
        description="MCP server for operating TinySA through serial port"
    )

    @mcp.tool()
    async def set_log_visible(visible: bool) -> dict:
        """
        Show or hide the log display in the GUI.
        Args:
            visible (bool): True to show, False to hide.
        Returns:
            dict: status and current visibility
        """
        global log_monitor
        if log_monitor:
            log_monitor.set_log_visible(visible)
            return {"status": "success", "visible": visible}
        else:
            return {"status": "error", "message": "Log monitor not initialized"}
    
    # ツール関数の登録
    @mcp.tool()
    async def get_version(port: str) -> Dict[str, Any]:
        """Get the version information of the TinySA device.
        
        Args:
            port: Serial port to connect to (explicitly required if not already set)
        """
        if not port and not tinySA.port:
            tinySA.log("Port parameter is required.", "ERROR")
            return {
                "status": "error",
                "message": "Port parameter is required."
            }
        try:
            if not tinySA.connect(port):
                return {
                    "status": "error",
                    "message": f"Failed to connect to TinySA on port {port}."
                }
            version_info = tinySA.get_version()
            return {
                "status": "success",
                "version_info": version_info
            }
        except Exception as e:
            tinySA.log(f"Error getting TinySA version: {e}", "ERROR")
            return {
                "status": "error",
                "message": f"Error getting TinySA version: {str(e)}"
            }
        finally:
            tinySA.disconnect()

    
    @mcp.tool()
    async def execute_command(command: str, port: str) -> Dict[str, Any]:
        """Execute a command on the TinySA device.
        
        Args:
            command: Command to execute.
            port: Serial port to connect to (explicitly required if not already set)
        """
        if not port and not tinySA.port:
            return {
                "status": "error",
                "message": "Port parameter is required."
            }
        try:
            if not tinySA.connect(port):
                return {
                    "status": "error",
                    "message": f"Failed to connect to TinySA on port {port}."
                }
            response = tinySA.send_command(command)
            return {
                "status": "success",
                "command": command,
                "response": response
            }
        except Exception as e:
            tinySA.log(f"Error executing command: {e}", "ERROR")
            return {
                "status": "error",
                "message": f"Error executing command: {str(e)}"
            }
        finally:
            tinySA.disconnect()
    
    @mcp.tool()
    async def get_device_info(port: str) -> Dict[str, Any]:
        """Get information about the connected TinySA device.
        
        Args:
            port: Serial port to connect to (explicitly required if not already set)
        """
        if not port and not tinySA.port:
            return {
                "status": "error",
                "message": "Port parameter is required."
            }
        try:
            if not tinySA.connect(port):
                return {
                    "status": "error",
                    "message": f"Failed to connect to TinySA on port {port}."
                }
            device_info = {
                "device": "TinySA",
                "port": tinySA.port or "Not connected",
                "connected": tinySA.connected,
                "baudrate": tinySA.baudrate,
            }
            try:
                device_info.update(tinySA.get_version())
            except Exception as e:
                device_info["version_error"] = str(e)
            return {
                "status": "success",
                "device_info": device_info
            }
        except Exception as e:
            tinySA.log(f"Error getting TinySA info: {e}", "ERROR")
            return {
                "status": "error",
                "message": f"Error getting TinySA info: {str(e)}"
            }
        finally:
            tinySA.disconnect()
    
    @mcp.tool()
    async def capture_image(port: str, save_name: Optional[str] = None, use_timestamp: bool = False) -> List[Union[types.ImageContent, types.TextContent]]:
        """
        Capture the TinySA screen image from the device and return it as an MCP Image.
        
        The function always returns the captured image as an MCP Image object.
        Additionally, it can save the image to a file if save_name is provided.
        
        Args:
            port: Serial port to connect to (explicitly required if not already set)
            save_name: Optional file path to save the captured image.
                    If None (default), the image is not saved to a file.
                    If provided, the image is saved to the specified file name.
            use_timestamp: Controls whether to add a timestamp to the filename.
                        Only applicable when save_path is provided.
        """
        if not port and not tinySA.port:
            tinySA.log("Port parameter is required.", "ERROR")
            raise Exception("Port parameter is required.")
        
        response = []  # レスポンスの初期化をtryブロックの外に移動
        
        try:
            if not tinySA.connect(port):
                tinySA.log(f"Failed to connect to TinySA on port {port}.", "ERROR")
                raise Exception(f"Failed to connect to TinySA on port {port}.")
            b = tinySA.get_image_data()
            if len(b) < 307200:
                tinySA.log(f"Insufficient data captured from device. len(data): {len(b)} < 307200", "ERROR")
                raise Exception(f"Insufficient data captured from device. len(data): {len(b)} < 307200")
            
            tinySA.log("Processing image data...")
            a = b[0:307200]
            x = struct.unpack(">153600H", a)
            arr = np.array(x, dtype=np.uint32)
            # 画像を適切なサイズに整形
            width = 480
            height = 320
            reshaped = arr.reshape(height, width)
            # そのままだとずれるので、少しシフトする
            shift_amount = width // 100  # 画面を見て調整
            # 各行をシフトして修正
            fixed_array = np.zeros_like(reshaped)
            for i in range(height):
                fixed_array[i] = np.roll(reshaped[i], -shift_amount)  # マイナス値で右シフト
            # 修正した配列を平坦化
            fixed_arr = fixed_array.flatten()
            # 色変換を続行
            fixed_arr = 0xFF000000 + ((fixed_arr & 0xF800) >> 8) + ((fixed_arr & 0x07EF) << 8) + ((fixed_arr & 0x001F) << 19)
            im = PILImage.frombuffer('RGBA', (480, 320), fixed_arr, 'raw', 'RGBA', 0, 1)
            
            # Save image to file if a path is specified
            if save_name:
                if use_timestamp:
                    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                    path_parts = os.path.splitext(save_name)
                    save_name = f"{path_parts[0]}_{timestamp}{path_parts[1]}"

                # Create 'img' directory in the current directory
                img_directory = os.path.join(os.getcwd(), 'img')
                os.makedirs(img_directory, exist_ok=True)

                # Update save_name to be within the img directory
                filename = os.path.basename(save_name)
                save_path = os.path.join(img_directory, filename)

                im.save(save_path)
                tinySA.log(f"Image saved to {save_path}")
                saved_filename = os.path.basename(save_path)
            
            buf = io.BytesIO()
            im.save(buf, format='PNG')
            b64_image = base64.b64encode(buf.getvalue()).decode('utf-8')
            
            # 画像データをレスポンスに追加
            response.append(
                types.ImageContent(
                    type="image", data=b64_image, mimeType="image/png"
                )
            )

            # ファイルが保存された場合は、ファイル名情報も追加
            if save_name:
                response.append(
                    types.TextContent(
                        type="text", text=f"Image saved as: {saved_filename}"
                    )
                )
            
            tinySA.log("Image capture completed successfully")
        except Exception as e:
            tinySA.log(f"Error capturing image: {e}", "ERROR")
            raise Exception(f"Error capturing image: {e}")
        finally:
            tinySA.disconnect()
        
        return response
     
    # MCPサーバーを実行して返す
    return mcp

# MCPサーバー実行用の関数
def run_mcp_server(mcp_server):
    # MCPサーバーの実行（この関数は別スレッドで実行される）
    mcp_server.run(transport='stdio')
    # サーバーrun()終了時にGUIも閉じる
    if log_monitor and hasattr(log_monitor, 'root'):
        log_monitor.root.after(0, log_monitor.root.destroy)
        
# メイン関数
def main():
    global log_monitor
    
    # Tkのルートウィンドウを作成
    root = tk.Tk()
    
    # ログモニターの初期化
    log_monitor = TinySALogMonitor(root)
    
    # MCPサーバーの初期化
    mcp_server = create_mcp_server(log_monitor.add_log)
    
    # 初期ログメッセージ
    log_monitor.add_log("[INFO] TinySA MCP Server Log Monitor started")
    
    # MCPサーバーを別スレッドで実行
    mcp_thread = threading.Thread(target=run_mcp_server, args=(mcp_server,), daemon=True)
    mcp_thread.start()
    
    # メインスレッドでGUIを実行
    root.mainloop()

# プログラム開始
if __name__ == "__main__":
    main()