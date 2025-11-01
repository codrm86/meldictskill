import os
import fluidsynth
import pydub
import wave
import numpy as np
from typing import Iterable
from engine.musicnotesequence import MusicNoteSequence
from engine.musicnote import MusicNote
from config import Config
from myconstants import *
from abspath import abs_path

def create_audio(opus_file: str,
                 wav_file: str,
                 soundfont_file: str,
                 vertical: bool,
                 *note_sequence: Iterable[MusicNote],
                 delete_wav = True,
                 note_duration_vertical: float = 2.7,
                 note_duration_arp: float = 0.9,
                 amplitude_multiplier: float = 6.3,
                 samplerate: int = 44100
                ):
    assert opus_file
    assert wav_file
    assert soundfont_file
    assert note_sequence

    synth: fluidsynth.Synth = None
    samples = np.array([], dtype=np.float32)

    try:
        synth = fluidsynth.Synth(samplerate=samplerate)
        sfid = synth.sfload(soundfont_file)
        synth.program_select(0, sfid, 0, 0)

        channel = 0
        note_samples = int(round(samplerate * (note_duration_vertical if vertical else note_duration_arp)))
        silent_samples = int(round(samplerate * 0.3))

        if vertical:
            for note in note_sequence:
                synth.noteon(channel, note.midi_code, 100)

            samples = np.append(samples, synth.get_samples(note_samples))

            for note in note_sequence:
                synth.noteoff(channel, note.midi_code)

            samples = np.append(samples, synth.get_samples(silent_samples)) # 0.3 секунды тишины в конце файла
        else:
            for note in note_sequence:
                synth.noteon(channel, note.midi_code, 100)
                samples = np.append(samples, synth.get_samples(note_samples))

            samples = np.append(samples, synth.get_samples(note_samples))

            for note in note_sequence:
                synth.noteoff(channel, note.midi_code)

            samples = np.append(samples, synth.get_samples(silent_samples)) # 0.3 секунды тишины в конце файла
    finally:
        if synth: synth.delete()

    try:
        # Multiply float samples by the amplitude multiplier, then clip
        # to the int16 range before converting to int16. Clipping prevents
        # overflow/wrap-around when writing PCM16 WAV frames.
        samples *= amplitude_multiplier
        samples = np.clip(samples, -32768.0, 32767.0)
        samples = samples.astype(np.int16)

        with wave.open(wav_file, mode="wb") as wav:
            wav.setnchannels(2)
            wav.setsampwidth(2) # int16, 2 bytes
            wav.setframerate(samplerate)
            wav.writeframes(samples.tobytes()) # записываем сэмплы с увеличением амплитуды

        segment = pydub.AudioSegment.from_wav(wav_file)
        segment.export(opus_file, format="opus", codec="libopus")
    finally:
        if delete_wav == True and os.path.isfile(wav_file):
            os.remove(wav_file)

def generate_audio(noteseq: MusicNoteSequence, replace_existing = True) -> bool:   
    assert noteseq
    config = Config()

    def file_name(ext):
        return os.path.join(abs_path(config.data.websounds_folder), f"{noteseq.file_name}{ext}")

    opus_file = file_name(OPUS_EXT)

    if not replace_existing and os.path.isfile(opus_file):
        return False

    create_audio(
            opus_file,
            file_name(WAV_EXT),
            abs_path(config.data.sound_font),
            noteseq.is_vertical,
            *noteseq,
            delete_wav=True)
    return True