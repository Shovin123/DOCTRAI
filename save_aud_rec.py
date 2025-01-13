import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import keyboard  # Requires 'keyboard' module to detect keypresses

# Parameters
sample_rate = 44100  # Sample rate in Hz
filename = 'output.wav'  # Output filename
chunk_duration = 0.5  # Duration of each chunk in seconds

# Create an empty list to hold audio data chunks
audio_chunks = []

print("Press 'Ctrl+C' to stop recording manually.")

try:
    print("Recording...")
    while True:
        # Record a small chunk of audio
        audio_chunk = sd.rec(int(chunk_duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
        sd.wait()  # Wait until this chunk is finished
        audio_chunks.append(audio_chunk)

except KeyboardInterrupt:
    print("Recording stopped manually.")

# Combine all audio chunks into a single array
audio_data = np.concatenate(audio_chunks, axis=0)

# Save the recorded audio as a .wav file
write(filename, sample_rate, audio_data)
print(f"Audio saved as {filename}.")
