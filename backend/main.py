
import os
import traceback
import subprocess
import tempfile
from pathlib import Path

import librosa
import numpy as np
import pretty_midi

from scipy.ndimage import median_filter
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SAMPLE_RATE = 22050
HOP_LENGTH = 256
FRAME_LENGTH = 2048

SOUNDFONT = Path(
    os.getenv(
        "VIOLIN_SOUNDFONT",
        str(BASE_DIR / "soundfonts" / "violin.sf2")
    )
)

FLUIDSYNTH = os.getenv(
    "FLUIDSYNTH_PATH",
    "fluidsynth"
)

OUTPUT_WAV = OUTPUT_DIR / "hum2violin.wav"

app = FastAPI(title="HUM2VIOLIN API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# CHECK CONFIGURATION
# --------------------------------------------------

def check_configuration():
    if not SOUNDFONT.is_file():
        raise RuntimeError(
            f"SoundFont not found: {SOUNDFONT}"
        )

    if Path(FLUIDSYNTH).is_file():
        return

    # If a full executable path was supplied, verify it.
    if "\\" in FLUIDSYNTH or "/" in FLUIDSYNTH:
        raise RuntimeError(
            f"FluidSynth executable not found: {FLUIDSYNTH}"
        )

    # Otherwise, check whether the executable is on PATH.
    import shutil

    if shutil.which(FLUIDSYNTH) is None:
        raise RuntimeError(
            "FluidSynth was not found. Set FLUIDSYNTH_PATH "
            "to the full path of fluidsynth.exe."
        )


# --------------------------------------------------
# PITCH DETECTION
# --------------------------------------------------

def extract_notes(audio_path):
    print("Loading humming audio...")

    audio, sr = librosa.load(
        str(audio_path),
        sr=SAMPLE_RATE,
        mono=True
    )

    if len(audio) < int(0.25 * sr):
        raise ValueError(
            "Audio is too short. Please record at least "
            "one second of humming."
        )

    if np.max(np.abs(audio)) < 1e-5:
        raise ValueError(
            "The audio is silent. Please upload a recording "
            "with audible humming."
        )

    print("Detecting pitches with librosa.pyin...")

    pitches, voiced_flags, probabilities = librosa.pyin(
        audio,
        fmin=librosa.note_to_hz("C2"),
        fmax=librosa.note_to_hz("C7"),
        sr=sr,
        frame_length=FRAME_LENGTH,
        hop_length=HOP_LENGTH
    )

    if pitches is None or not np.any(np.isfinite(pitches)):
        raise ValueError(
            "No clear humming melody detected. "
            "Try a clearer recording with less background noise."
        )

    # Convert detected frequencies to MIDI note numbers.
    midi_pitches = np.full(len(pitches), -1, dtype=int)
    valid = np.isfinite(pitches) & voiced_flags

    midi_pitches[valid] = np.rint(
        librosa.hz_to_midi(pitches[valid])
    ).astype(int)

    # Smooth small pitch fluctuations.
    if len(midi_pitches) >= 5:
        smoothed = median_filter(
            midi_pitches.astype(float),
            size=5,
            mode="nearest"
        ).astype(int)

        # Preserve unvoiced frames.
        midi_pitches[valid] = smoothed[valid]

    frame_duration = HOP_LENGTH / sr
    notes = []

    current_pitch = None
    start_time = 0.0

    for i, pitch in enumerate(midi_pitches):
        time = i * frame_duration

        if pitch != current_pitch:
            if current_pitch is not None:
                end_time = time

                if end_time - start_time >= 0.08:
                    notes.append(
                        (current_pitch, start_time, end_time)
                    )

            current_pitch = pitch if pitch >= 0 else None
            start_time = time

    # Add the final detected note.
    final_time = len(midi_pitches) * frame_duration

    if current_pitch is not None:
        if final_time - start_time >= 0.08:
            notes.append(
                (current_pitch, start_time, final_time)
            )

    if not notes:
        raise ValueError(
            "Could not extract any usable notes from the humming."
        )

    print(f"Detected {len(notes)} notes.")

    return notes


# --------------------------------------------------
# CREATE MIDI FILE
# --------------------------------------------------

def create_midi(notes, midi_path):
    midi = pretty_midi.PrettyMIDI()

    # General MIDI program 40 (zero-based) = Violin.
    violin = pretty_midi.Instrument(program=40)

    for pitch, start, end in notes:
        start = max(0.0, float(start))
        end = max(start + 0.08, float(end))

        violin.notes.append(
            pretty_midi.Note(
                velocity=95,
                pitch=int(pitch),
                start=start,
                end=end
            )
        )

    midi.instruments.append(violin)
    midi.write(str(midi_path))

    print(f"MIDI created: {midi_path}")


# --------------------------------------------------
# RENDER MIDI USING FLUIDSYNTH
# --------------------------------------------------

def render_violin(midi_path, wav_path):
    check_configuration()

    command = [
        FLUIDSYNTH,
        "-ni",
        "-g", "0.8",
        "-r", str(SAMPLE_RATE),
        "-T", "wav",
        "-F", str(wav_path),
        str(SOUNDFONT),
        str(midi_path)
    ]

    print("Running FluidSynth...")
    print("SoundFont:", SOUNDFONT)
    print("Executable:", FLUIDSYNTH)

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120,
            check=False
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Cannot start FluidSynth: {exc}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            "FluidSynth timed out while generating audio."
        ) from exc

    if result.stdout:
        print("FluidSynth output:", result.stdout[-2000:])

    if result.stderr:
        print("FluidSynth messages:", result.stderr[-3000:])

    if result.returncode != 0:
        raise RuntimeError(
            f"FluidSynth exited with code {result.returncode}. "
            f"Output: {(result.stderr or result.stdout)[-2000:]}"
        )

    if not wav_path.is_file() or wav_path.stat().st_size < 100:
        raise RuntimeError(
            "FluidSynth finished without creating a valid WAV file."
        )

    print("Violin audio generated successfully.")


# --------------------------------------------------
# API ROUTES
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "message": "HUM2VIOLIN backend is running.",
        "convert_endpoint": "/convert"
    }


@app.get("/health")
def health():
    return {
        "status": "running",
        "soundfont_exists": SOUNDFONT.is_file(),
        "soundfont_path": str(SOUNDFONT),
        "fluidsynth_executable": FLUIDSYNTH
    }


@app.post("/convert")
async def convert(file: UploadFile = File(...)):
    temp_audio = None
    temp_midi = None

    try:
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="Please select an audio file."
            )

        if Path(file.filename).suffix.lower() != ".wav":
            raise HTTPException(
                status_code=400,
                detail="Please upload a WAV file."
            )

        audio_bytes = await file.read()

        if not audio_bytes:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty."
            )

        if len(audio_bytes) > 50 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="File is too large. Maximum size is 50 MB."
            )

        # Save uploaded audio to a temporary WAV file.
        with tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False
        ) as temp:
            temp.write(audio_bytes)
            temp_audio = Path(temp.name)

        # Generate temporary MIDI.
        with tempfile.NamedTemporaryFile(
            suffix=".mid",
            delete=False
        ) as temp:
            temp_midi = Path(temp.name)

        print(f"Received file: {file.filename}")
        print(f"File size: {len(audio_bytes)} bytes")

        # Extract notes, create MIDI, render violin.
        notes = extract_notes(temp_audio)
        create_midi(notes, temp_midi)
        render_violin(temp_midi, OUTPUT_WAV)

        return FileResponse(
            path=str(OUTPUT_WAV),
            media_type="audio/wav",
            filename="hum2violin.wav"
        )

    except HTTPException:
        raise

    except Exception as exc:
        print("\n========== HUM2VIOLIN ERROR ==========")
        traceback.print_exc()
        print("======================================\n")

        # Return the real error during local debugging.
        raise HTTPException(
            status_code=500,
            detail=f"{type(exc).__name__}: {exc}"
        ) from exc

    finally:
        if temp_audio is not None:
            temp_audio.unlink(missing_ok=True)

        if temp_midi is not None:
            temp_midi.unlink(missing_ok=True)
