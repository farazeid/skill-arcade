import asyncio
import json

from fastapi import WebSocket, WebSocketDisconnect

from src.game import Game

TICK_RATE = 1 / 60  # Aim for 60 FPS


async def game_loop(websocket: WebSocket, game: Game) -> None:
    """The main loop that drives a single game instance and sends updates."""

    # For FPS calculation
    loop = asyncio.get_event_loop()
    last_fps_time = loop.time()
    frame_count = 0
    server_fps = 0.0

    current_action_name = "NOOP"

    while True:
        try:
            # --- Handle all incoming client messages ---
            # Drain the websocket queue to get the most recent action
            while True:
                try:
                    message_str = await asyncio.wait_for(
                        websocket.receive_text(), timeout=0.001
                    )
                    message = json.loads(message_str)

                    if message.get("type") == "action" and "action" in message:
                        current_action_name = message["action"]

                except asyncio.TimeoutError:
                    # No more messages in the queue
                    break
                except WebSocketDisconnect:
                    raise  # Re-raise to be caught by the outer loop
                except Exception:
                    # Ignore other message-related errors
                    pass

            # --- Determine action for this tick ---
            # The frontend sends the complete action name (e.g., "UPRIGHTFIRE")
            action_for_this_tick = game.action_ids.get(
                current_action_name, game.action_ids.get("NOOP", 0)
            )

            # Update the game state with the action for this tick
            game.step(action_for_this_tick)

            # --- FPS Calculation ---
            frame_count += 1
            current_time = loop.time()
            if current_time - last_fps_time >= 1.0:
                server_fps = frame_count / (current_time - last_fps_time)
                frame_count = 0
                last_fps_time = current_time

            # Send the new state to the client
            state = game.get_state()
            state["serverFps"] = round(server_fps, 1)
            await websocket.send_text(json.dumps(state))

        except WebSocketDisconnect:
            print("Client disconnected. Ending game loop.")
            break
        except Exception as e:
            print(f"An error occurred in the game loop: {e}")
            break

        # Control the game's speed
        await asyncio.sleep(TICK_RATE)
