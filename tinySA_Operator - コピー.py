import serial
import time
from typing import Dict, Any, Optional, List, Union
import base64
import os  # Added for connection management in capture_image
from mcp.server.fastmcp import FastMCP, Image
import mcp.types as types
import struct
import numpy as np
import datetime
from PIL import Image as PILImage
import io

class TinySASerial:
    """Class to handle serial communication with TinySA device."""
    
    def __init__(self, port: Optional[str] = None, baudrate: int = 9600):
        self.port = port
        self.baudrate = baudrate
        self.timeout = 3
        self.serial_conn: Optional[serial.Serial] = None
        self.connected = False
    
    def connect(self, port: Optional[str] = None) -> bool:
        """Connect to TinySA device. Port is required if not already set."""
        if port:
            self.port = port
        if not self.port:
            print("Error: Port parameter is required for connection.")
            return False
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=self.timeout
            )
            self.connected = True
            return True
        except (serial.SerialException, OSError) as e:
            print(f"Error connecting to TinySA: {e}")
            self.connected = False
            return False
    
    def disconnect(self) -> None:
        """Disconnect from TinySA device."""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        self.connected = False

    def get_image_data(self) -> bytearray:
        """Get screen data from TinySA device."""
        if self.serial_conn and self.serial_conn.is_open:
            # Clear any pending data
            self.serial_conn.reset_input_buffer()
            self.serial_conn.write("capture\r".encode('utf-8'))
            data = self.serial_conn.read(307200)
            ans = bytearray(307200)
            ans[0:len(data)] = data            
            return ans
        else:
            raise Exception("Not connected to TinySA device. Please execute connect command.")

    def send_command(self, command: str, wait_time: float = 0.1) -> str:
        """Send command to TinySA and return response."""
        if not self.connected or not self.serial_conn:
            raise Exception("Not connected to TinySA device. Please execute connect command.")
        
        try:
            # Clear any pending data
            self.serial_conn.reset_input_buffer()
            
            # Send command with newline
            cmd = command.strip() + "\r\n"
            self.serial_conn.write(cmd.encode('utf-8'))
            
            # Wait for device to process command
            time.sleep(wait_time)
            
            # Read response
            response = ""
            while self.serial_conn.in_waiting:
                response += self.serial_conn.read(self.serial_conn.in_waiting).decode('utf-8', errors='replace')
                time.sleep(0.1)  # Small delay to ensure all data is received
            
            return response.strip()
        except (serial.SerialException, OSError) as e:
            raise Exception(f"Error communicating with TinySA: {e}")
    
    def get_version(self) -> Dict[str, str]:
        """Get TinySA version information."""
        try:
            # Send version command
            response = self.send_command("version")
            
            # Parse version information
            version_info = {
                "raw_response": response
            }
            
            # Split the response into lines
            lines = response.strip().split('\n')
            
            # First line typically contains the firmware version
            #1行目はローカルエコーなので、2行目と3行目がバージョン情報になる。ローカルエコーは要注意
            if lines and len(lines) >= 2:
                version_info["firmware"] = lines[1].strip()
            if lines and len(lines) >= 3:
                version_info["hardware"] = lines[2].strip()
            
            return version_info
        except Exception as e:
            raise Exception(f"Error getting TinySA version: {e}")


# Initialize FastMCP server
mcp = FastMCP(
    name="tinySA-operator",
    version="0.1.0",
    description="MCP server for operating TinySA through serial port"
)

# Create a global TinySA instance
tinySA = TinySASerial()


# Tool functions with internal connection management

@mcp.tool()
async def get_version(port: str) -> Dict[str, Any]:
    """Get the version information of the TinySA device.
    
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
        version_info = tinySA.get_version()
        return {
            "status": "success",
            "version_info": version_info
        }
    except Exception as e:
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
        raise Exception("Port parameter is required.")
    
    response = []  # レスポンスの初期化を try ブロックの外に移動
    
    try:
        if not tinySA.connect(port):
            raise Exception(f"Failed to connect to TinySA on port {port}.")
        b = tinySA.get_image_data()
        if len(b) < 307200:
            raise Exception(f"Insufficient data captured from device. len(data): {len(b)} < 307200")
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
            save_path = os.path.join(img_directory, filename)  # save_path として新しい変数を使用

            im.save(save_path)
            print(f"Image saved to {save_path}")
            saved_filename = os.path.basename(save_path)  # 保存された実際のファイル名
        
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
    except Exception as e:
        raise Exception(f"Error capturing image: {e}")
    finally:
        tinySA.disconnect()
    
    return response  # try ブロックの外で return を追加



if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')