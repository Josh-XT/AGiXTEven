import time
import asyncio
from RealtimeSTT import AudioToTextRecorder
from even_glasses.bluetooth_manager import GlassesManager
from even_glasses.commands import send_text
from even_glasses.notification_handlers import handle_incoming_notification
from agixtsdk import AGiXTSDK
import time


def transcribe_words(alignment_data, group_size=3, time_shift=1.0):
    """
    Processes alignment data to group words with adjusted timestamps.

    Args:
        alignment_data (dict): Alignment data from the speech synthesis.
        group_size (int): Number of words per group.
        time_shift (float): Time in seconds to shift the timestamps earlier.

    Returns:
        list: A list of word groups with adjusted timestamps.
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

    # Add the last word if it exists
    if current_word:
        words.append(
            {
                "word": current_word,
                "start_time": word_start - time_shift,
                "end_time": word_end - time_shift,
            }
        )

    # Group words based on the specified group size
    grouped_words = [
        words[i : i + group_size] for i in range(0, len(words), group_size)
    ]

    return grouped_words


def print_with_timestamps(grouped_words):
    """
    Prints word groups according to their timestamps.

    Args:
        grouped_words (list): List of word groups with timestamps.
    """

    for group in grouped_words:
        print(" ".join([word["word"] for word in group]))
        time.sleep(group[-1]["end_time"] - group[0]["start_time"])
        print(
            f"Start: {group[0]['start_time']:.2f}s, "
            f"End: {group[-1]['end_time']:.2f}s"
        )


async def get_manager():
    manager = GlassesManager(left_address=None, right_address=None)
    connected = await manager.scan_and_connect()

    if connected:
        # Assign notification handlers
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

    Args:
        message (str): The message to display.
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


def process_text(manager, text, agent_name="XT"):
    print(f"Transcribed text: {text}")
    asyncio.run(send_text(manager=manager, text_message=text, duration=1))
    # Send text to AGiXT
    agixt = AGiXTSDK()
    asyncio.run(send_text(manager=manager, text_message="Thinking...", duration=2))
    response = agixt.prompt_agent(
        agent_name=agent_name,
        prompt_name="Think About It",
        prompt_args={"user_input": text},
    )
    print(f"AGiXT response: {response}")
    display_message(manager, response)
    return response


async def main():
    manager = await get_manager()

    with AudioToTextRecorder(
        model="small",
        wake_words="jarvis",
        on_recording_start=lambda: my_start_callback(manager),
        on_recording_stop=lambda: my_stop_callback(manager),
        wakeword_backend="oww",
        wake_words_sensitivity=0.35,
        wake_word_buffer_duration=1,
    ) as recorder:
        print('Say "Jarvis" to start recording.')
        # Start listening and processing text
        while True:
            recorder.text(
                lambda text: process_text(manager=manager, text=text, agent_name="XT")
            )


if __name__ == "__main__":
    asyncio.run(main())
