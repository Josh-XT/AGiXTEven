import time
import asyncio
import threading
from datetime import datetime
from agixtsdk import AGiXTSDK
from RealtimeSTT import AudioToTextRecorder
from even_glasses.commands import send_text
from even_glasses.bluetooth_manager import GlassesManager
from even_glasses.notification_handlers import handle_incoming_notification


def transcribe_words(alignment_data, group_size=3, time_shift=1.0):
    """
    Processes alignment data to group words with adjusted timestamps.
    """
    chars = alignment_data["alignment"]["characters"]
    starts = alignment_data["alignment"]["character_start_times_seconds"]
    ends = alignment_data["alignment"]["character_end_times_seconds"]

    words = []
    current_word = ""
    word_start = None
    word_end = None

    for char, start, end in zip(chars, starts, ends):
        if char.strip() == "":
            if current_word:
                words.append(
                    {
                        "word": current_word,
                        "start_time": word_start - time_shift,
                        "end_time": word_end - time_shift,
                    }
                )
                current_word = ""
                word_start = None
                word_end = None
            continue
        if current_word == "":
            word_start = start
        current_word += char
        word_end = end

    if current_word:
        words.append(
            {
                "word": current_word,
                "start_time": word_start - time_shift,
                "end_time": word_end - time_shift,
            }
        )

    grouped_words = [
        words[i : i + group_size] for i in range(0, len(words), group_size)
    ]
    return grouped_words


def print_with_timestamps(grouped_words):
    """
    Prints word groups according to their timestamps.
    """
    for group in grouped_words:
        print(" ".join([word["word"] for word in group]))
        time.sleep(group[-1]["end_time"] - group[0]["start_time"])
        print(
            f"Start: {group[0]['start_time']:.2f}s, End: {group[-1]['end_time']:.2f}s"
        )


async def get_manager():
    manager = GlassesManager(left_address=None, right_address=None)
    connected = await manager.scan_and_connect()

    if connected:
        if manager.left_glass:
            manager.left_glass.notification_handler = handle_incoming_notification
        if manager.right_glass:
            manager.right_glass.notification_handler = handle_incoming_notification
    else:
        print("No glasses found. Please ensure they are powered on and in range.")
    return manager


def my_start_callback(manager):
    print("Recording started!")
    asyncio.run(send_text(manager=manager, text_message="Listening...", duration=1))


def my_stop_callback(manager):
    print("Recording stopped!")
    asyncio.run(send_text(manager=manager, text_message="Thinking...", duration=0.5))


def display_message(manager, alignment_data, group_size=7):
    """
    Displays a message on the screen.
    """
    words = transcribe_words(alignment_data, group_size=group_size)
    for group in words:
        print(" ".join([word["word"] for word in group]))
        asyncio.run(
            send_text(
                manager=manager,
                text_message=" ".join([word["word"] for word in group]),
                duration=abs(group[-1]["end_time"] - group[0]["start_time"]),
            )
        )
        time.sleep(group[-1]["end_time"] - group[0]["start_time"])


def process_text(
    manager: GlassesManager,
    text: str,
    sdk: AGiXTSDK,
    agent_name: str = "XT",
):
    print(f"Transcribed text: {text}")
    asyncio.run(send_text(manager=manager, text_message=text, duration=1))
    stop_event = threading.Event()

    def periodic_thinking():
        while not stop_event.wait(3):  # Waits 3 seconds or until event is set
            asyncio.run(
                send_text(manager=manager, text_message="Thinking...", duration=2)
            )

    thinking_thread = threading.Thread(target=periodic_thinking)
    thinking_thread.start()

    # Make the blocking call to AGiXT
    date_string = datetime.now().strftime("%Y-%m-%d")
    response = sdk.prompt_agent(
        agent_name=agent_name,
        prompt_name="Think About It",
        prompt_args={"user_input": text, "conversation_name": date_string},
    )

    # Signal the periodic thread to stop and wait for it to finish
    stop_event.set()
    thinking_thread.join()

    print(f"AGiXT response: {response}")
    display_message(manager, response)
    return response


async def main(sdk: AGiXTSDK, agent_name: str, wake_word: str = "jarvis"):
    manager = await get_manager()
    with AudioToTextRecorder(
        model="small",
        wake_words=wake_word,
        on_recording_start=lambda: my_start_callback(manager),
        on_recording_stop=lambda: my_stop_callback(manager),
        wakeword_backend="oww",
        wake_words_sensitivity=0.35,
        wake_word_buffer_duration=1,
    ) as recorder:
        print(f'Say "{wake_word}" to start recording.')
        while True:
            recorder.text(
                lambda text: process_text(
                    manager=manager,
                    text=text,
                    sdk=sdk,
                    agent_name=agent_name,
                )
            )


if __name__ == "__main__":
    import argparse
    import pyotp

    parser = argparse.ArgumentParser(description="Even Realities AGiXT Interface")
    parser.add_argument(
        "--agixt_server",
        type=str,
        help="AGiXT Server URI (e.g., http://localhost:7437)",
    )
    parser.add_argument(
        "--email",
        type=str,
        help="Email for AGiXT login",
    )
    parser.add_argument(
        "--otp",
        type=str,
        help="One-time password for MFA (Can use the 6-digit code or the secret key)",
    )
    parser.add_argument(
        "--agent_name",
        type=str,
        help="Agent name to use for the prompt",
        default="XT",
    )
    parser.add_argument(
        "--wake_word",
        type=str,
        help="Wake word to use for the recorder",
        default="jarvis",
    )
    args = parser.parse_args()
    agixt_uri = args.agixt_server or "http://localhost:7437"
    otp = args.otp
    email = args.email
    agent_name = args.agent_name
    wake_word = args.wake_word
    sdk = AGiXTSDK(base_uri=agixt_uri)
    if len(str(otp)) == 6:
        otp = pyotp.TOTP(otp).now()

    sdk.login(email=email, otp=otp)

    asyncio.run(main(sdk=sdk, agent_name=agent_name, wake_word=wake_word))
