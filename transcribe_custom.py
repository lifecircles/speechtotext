#!/usr/bin/env python

# Copyright 2019 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.



""" Speech-to-text with Google Cloud Speech API.
    - Written for MP3/WAV files of any sample rate and channel count.
    - Performs speaker diarization (distinguishing of speakers) with a
      default speaker count of 1. (command line argument -s)
    - Add phrase hints to boost the probability that such words/phrases
      will be recognized. (command line argument --w)

Example usage:
    python transcribe_custom.py --help
    python transcribe_custom.py resources/multi.wav -s 2 --w runway delay
"""

import argparse
from pydub import AudioSegment
import io
import os
import wave
import time
from google.cloud import speech_v1p1beta1 as speech


def parse_command_line():
    """Parses command line arguments."""

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        'path', help='File or GCS path for audio file to be recognized')
    parser.add_argument(
        '-s', help='Number of speakers - default set to 1 if argument not provided')
    parser.add_argument(
        '--w', nargs='*', help='Words to add as hints for the recognizer')
    args = parser.parse_args()
    if args.path.startswith('gs://'):
        transcribe_gcs(args.path)
    else:
        if args.s == None:
            args.s = "1"
        transcribe_file(args.path, args.w, int(args.s))


def mp3_to_wav(audio_file_name):
    """Convert a MP3 file to a WAV file. Returns new file name if applicable."""

    if audio_file_name.split('.')[1] == 'mp3':
        sound = AudioSegment.from_mp3(audio_file_name)
        new_audio_file_name = audio_file_name.split('.')[0] + '.wav'
        sound.export(new_audio_file_name, format="wav")

    else:
        new_audio_file_name = audio_file_name

    return new_audio_file_name


def get_frame_rate_channel(audio_file_name):
    """Gets the frame rate and number of channels."""

    with wave.open(audio_file_name, "rb") as wave_file:
        frame_rate = wave_file.getframerate()
        channels = wave_file.getnchannels()

    return frame_rate, channels


def trim_audio(audio_file_name):
    """Trims audio to 59 seconds."""

    sound = AudioSegment.from_file(audio_file_name, format="wav")
    if len(sound) > 59000:
        new_sound = sound[:59000]
        new_sound.export(audio_file_name, format="wav")


def write_file(transcript):
    """Writes a transcript to a file named with the timestamp."""

    filename = time.strftime("%Y%m%d-%H%M%S.txt")
    f = open(filename, "w+")
    f.write(transcript)
    print("Transcript saved to %s\n" % filename)
    f.close()


def write_vocab(words, filename):
    """Writes new vocabulary to an existing vocabulary file."""

    write_str = ""
    for i in words:
        write_str += "%s\n" % i

    f = open(filename, "w")
    f.write(write_str)
    f.close()


def load_vocab(filename):
    """Returns the vocabulary file in the form of a list."""

    f = open(filename, "r")
    words = f.read().split('\n')
    words = list(filter(None, words))
    f.close()
    return words


def transcribe_file(speech_file, hints, speakers):
    """Transcribe the given audio file synchronously."""

    AudioSegment.converter = "C:\\ffmpeg\\bin\\ffmpeg.exe"  # Set to location of ffmpeg.exe
    speech_file = mp3_to_wav(speech_file)
    frame_rate, channels = get_frame_rate_channel(speech_file)
    trim_audio(speech_file)

    client = speech.SpeechClient()

    with open(speech_file, 'rb') as audio_file:
        content = audio_file.read()

    audio = speech.types.RecognitionAudio(content=content)

    # Load and add vocabulary hints
    words = load_vocab("vocab.txt")
    words_set = set(words)
    if hints is not None:
        for i in hints:
            if i not in words_set:
                words.append(i)
        write_vocab(words, "vocab.txt")

    config = speech.types.RecognitionConfig(
        encoding=speech.enums.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=frame_rate,
        language_code='en-US',
        audio_channel_count=channels,
        enable_separate_recognition_per_channel=True,
        enable_speaker_diarization=True,
        diarization_speaker_count=speakers,
        enable_automatic_punctuation=True,
        speech_contexts=[{"phrases": words}])

    print('Waiting for operation to complete...\n')
    response = client.recognize(config, audio)

    # The transcript within each result is separate and sequential per result.
    # However, the words list within an alternative includes all the words
    # from all the results thus far. Thus, to get all the words with speaker
    # tags, you only have to take the words list from the last result:

    result = response.results[-1]
    words_info = result.alternatives[0].words

    transcript = ""
    tag = 1
    speaker = ""

    # Printing out the output:
    for word_info in words_info:
        if word_info.speaker_tag == tag:
            speaker = speaker + " " + word_info.word
        else:
            transcript += "Speaker {}: {}".format(tag, speaker) + '\n'
            tag = word_info.speaker_tag
            speaker = "" + word_info.word

    transcript += "Speaker {}: {}".format(tag, speaker)
    transcript += "\n"

    print(transcript)
    write_file(transcript)  # Write to timestamped file


############ FOR FUTURE DEVELOPMENT WITH FILES STORED ON GOOGLE CLOUD ############
def transcribe_gcs(gcs_uri):
    """Transcribe the given audio file on GCS."""
    # [START speech_transcribe_multichannel_gcs]
    from google.cloud import speech
    client = speech.SpeechClient()

    audio = speech.types.RecognitionAudio(uri=gcs_uri)

    config = speech.types.RecognitionConfig(
        encoding=speech.enums.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=44100,
        language_code='en-US',
        audio_channel_count=2,
        enable_separate_recognition_per_channel=True)

    response = client.recognize(config, audio)

    for i, result in enumerate(response.results):
        alternative = result.alternatives[0]
        print('-' * 20)
        print('First alternative of result {}'.format(i))
        print(u'Transcript: {}'.format(alternative.transcript))
        print(u'Channel Tag: {}'.format(result.channel_tag))
    # [END speech_transcribe_multichannel_gcs]


if __name__ == '__main__':
    parse_command_line()

