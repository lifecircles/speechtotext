from pynput import keyboard
import time
import pyaudio
import wave
import sched
import sys
import os

CHUNK = 8192
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

p = pyaudio.PyAudio()
frames = []


def callback(in_data, frame_count, time_info, status):
    frames.append(in_data)
    return (in_data, pyaudio.paContinue)


class MyListener(keyboard.Listener):
    def __init__(self):
        super(MyListener, self).__init__(self.on_press, self.on_release)
        self.key_pressed = None
        self.wf = None
        self.ended = None

    def on_press(self, key):
        if key.char == 'r':
            self.key_pressed = True
        elif key.char == 'q':
            self.ended = True
        return True

    def on_release(self, key):
        if key.char == 'r':
            self.key_pressed = False
        return True

    def write_file(self, frames):
        # Create and write to audio file named with current timestamp
        filename = time.strftime("%Y%m%d-%H%M%S.wav")
        self.wf = wave.open(filename, 'wb')
        self.wf.setnchannels(CHANNELS)
        self.wf.setsampwidth(p.get_sample_size(FORMAT))
        self.wf.setframerate(RATE)
        self.wf.writeframes(b''.join(frames))
        self.wf.close()
        return filename


def recorder():
    global started, p, stream, frames, recording

    if listener.key_pressed and not recording:
        # Start the recording
        try:
            stream = p.open(format=FORMAT,
                             channels=CHANNELS,
                             rate=RATE,
                             input=True,
                             frames_per_buffer=CHUNK,
                             stream_callback = callback)
            recording = True
            print("Started recording")
        except:
            raise

    elif not listener.key_pressed and recording:
        print("Stopped recording")
        recording = False
        stream.stop_stream()
        filename = listener.write_file(frames)
        print("Recording saved to %s\n" % filename)
        os.system('python transcribe_custom.py {} -s 1'.format(filename))
        frames = []     # Reset frames
        print("Press and hold the 'r' key to begin recording")
        print("Release the 'r' key to end recording")
        print("Press the 'q' key to quit session\n")

    elif not listener.key_pressed and listener.ended:
        # Quit the session
        stream.close()
        p.terminate()
        print("Quitting session")
        sys.exit()

    # Reschedule the recorder function in 100 ms.
    task.enter(0.1, 1, recorder, ())


if __name__ == "__main__":
    listener = MyListener()
    listener.start()
    recording = False
    stream = None

    print("Press and hold the 'r' key to begin recording")
    print("Release the 'r' key to end recording")
    print("Press the 'q' key to quit session\n")

    task = sched.scheduler(time.time, time.sleep)
    task.enter(0.1, 1, recorder, ())
    task.run()

