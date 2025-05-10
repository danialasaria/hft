import asyncio
import websockets

async def test_binance_connection(uri):
    print(f"Attempting to connect to: {uri}")
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Successfully connected to {uri}!")
            # Optionally, try to receive a message
            # try:
            #     message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            #     print(f"Received first message: {message[:100]}...") # Print first 100 chars
            # except asyncio.TimeoutError:
            #     print("Timed out waiting for first message, but connection was successful.")
            # except Exception as e:
            #     print(f"Error receiving message: {e}")
            await websocket.close()
            print("Connection closed.")
            return True
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"Failed to connect to {uri}. InvalidStatusCode: {e.status_code} {e.headers}")
        if e.status_code == 451:
            print("Error 451: Unavailable For Legal Reasons. This likely means a regional block.")
    except ConnectionRefusedError:
        print(f"Failed to connect to {uri}. Connection refused.")
    except Exception as e:
        print(f"Failed to connect to {uri}. An unexpected error occurred: {e}")
    return False

async def main():
    # Test with stream.binance.com:9443 (original)
    # uri_spot_9443 = "wss://stream.binance.com:9443/ws/btcusdt@trade"
    # print("--- Testing stream.binance.com:9443 (Spot) ---")
    # await test_binance_connection(uri_spot_9443)
    # print("\n")

    # Test with stream.binance.com:443 (alternative spot port)
    # uri_spot_443 = "wss://stream.binance.com:443/ws/btcusdt@trade"
    # print("--- Testing stream.binance.com:443 (Spot) ---")
    # await test_binance_connection(uri_spot_443)
    # print("\n")

    # Test with data-stream.binance.vision (dedicated market data endpoint)
    uri_data_vision = "wss://data-stream.binance.vision/ws/btcusdt@trade"
    print("--- Testing data-stream.binance.vision (Market Data Only) ---")
    await test_binance_connection(uri_data_vision)
    print("\n")

    # Test with fstream.binance.com (Futures)
    # uri_futures = "wss://fstream.binance.com/ws/btcusdt@aggTrade" # aggTrade is common for futures
    # print("--- Testing fstream.binance.com (Futures) ---")
    # await test_binance_connection(uri_futures)
    # print("\n")

if __name__ == "__main__":
    asyncio.run(main()) 