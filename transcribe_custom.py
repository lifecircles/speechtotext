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
      default speaker count of 2. Edit the value of [diarization_speaker_count]
      in the [config] variable if necessary.

Example usage:
    python transcribe_custom.py resources/multi.wav
    python transcribe_custom.py \
        gs://cloud-samples-tests/speech/multi.wav
"""

import argparse
from pydub import AudioSegment
import io
import os
import wave
from google.cloud import speech_v1p1beta1 as speech


def mp3_to_wav(audio_file_name):
    """Convert a MP3 file to a WAV file."""

    if audio_file_name.split('.')[1] == 'mp3':
        sound = AudioSegment.from_mp3(audio_file_name)
        audio_file_name = audio_file_name.split('.')[0] + '.wav'
        sound.export(audio_file_name, format="wav")


def get_frame_rate_channel(audio_file_name):
    """Gets the frame rate and number of channels."""

    with wave.open(audio_file_name, "rb") as wave_file:
        frame_rate = wave_file.getframerate()
        channels = wave_file.getnchannels()

    return frame_rate, channels


def transcribe_file(speech_file):
    """Transcribe the given audio file synchronously."""
    # [START speech_transcribe_multichannel]
    # from google.cloud import speech
    mp3_to_wav(speech_file)
    frame_rate, channels = get_frame_rate_channel(speech_file)

    client = speech.SpeechClient()

    with open(speech_file, 'rb') as audio_file:
        content = audio_file.read()

    audio = speech.types.RecognitionAudio(content=content)

    config = speech.types.RecognitionConfig(
        encoding=speech.enums.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=frame_rate,
        language_code='en-US',
        audio_channel_count=channels,
        enable_separate_recognition_per_channel=True,
        enable_speaker_diarization=True,
        diarization_speaker_count=2,
        enable_automatic_punctuation=True)

    print('Waiting for operation to complete...')
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
            transcript += "speaker {}: {}".format(tag, speaker) + '\n'
            tag = word_info.speaker_tag
            speaker = "" + word_info.word

    transcript += "Speaker {}: {}".format(tag, speaker)

    print(transcript)


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
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        'path', help='File or GCS path for audio file to be recognized')
    args = parser.parse_args()
    if args.path.startswith('gs://'):
        transcribe_gcs(args.path)
    else:
        transcribe_file(args.path)
