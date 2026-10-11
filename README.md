# HUM2VIOLIN 🎻

HUM2VIOLIN is a simple application that converts a humming recording into a violin rendition of the melody.

Users upload a WAV audio file, and the application detects the musical notes in the humming and recreates them using a violin sound.

## Features

- Upload a humming recording in WAV format.
- Detect the melody and estimate its musical notes.
- Convert the detected notes into MIDI instructions.
- Generate violin audio using a violin SoundFont.
- Listen to and download the generated WAV file.

## Workflow

The application follows these steps:

1. **Audio Input:** The user uploads a WAV recording of humming.
2. **Pitch Detection:** Librosa and pYIN analyze the recording to estimate pitches and timings.
3. **Note Processing:** The detected notes are smoothed and organized into a sequence.
4. **MIDI Generation:** Pretty MIDI converts the note sequence into MIDI instructions.
5. **Violin Synthesis:** FluidSynth uses the MIDI instructions and a violin SoundFont to generate audio.
6. **Audio Output:** The application returns the generated violin WAV file to the user.

**Workflow:**

`Humming WAV → Pitch Detection → MIDI Generation → Violin Synthesis → Violin WAV`

## Technologies Used

- **Python** – Backend development
- **FastAPI** – Backend API
- **Librosa** – Audio processing and pitch detection
- **pYIN** – Fundamental frequency estimation
- **Pretty MIDI** – MIDI note generation
- **FluidSynth** – Instrument sound synthesis
- **SoundFont (.sf2)** – Provides instrument sounds
- **React** – Frontend interface
- **Vite** – Frontend development server

## Project Structure

```text
Hum2Violin/
├── backend/
│   ├── main.py
│   ├── soundfonts/
│   │   └── violin.sf2
│   ├── outputs/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   └── App.css
│   ├── package.json
│   └── index.html
├── .gitignore
└── README.md
```

*Note: The structure above is illustrative. Include only files and folders that actually exist in your repository.*

## Requirements

Install the following before running the application:

- Python 3.10 or a compatible Python version
- Node.js and npm
- FluidSynth
- A compatible violin SoundFont file (`.sf2`)

## How to Run the Backend

### 1. Open a terminal

Navigate to the `backend` directory inside the project folder:

```powershell
cd "path-to-project\backend"
```

Replace `path-to-project` with the location of your cloned or downloaded project.

### 2. Install Python dependencies

If a `requirements.txt` file is available, run:

```powershell
python -m pip install -r requirements.txt
```

Otherwise, install the required packages:

```powershell
python -m pip install fastapi "uvicorn[standard]" python-multipart librosa numpy pretty_midi scipy
```

### 3. Configure FluidSynth and the SoundFont

Set the paths to the FluidSynth executable and the violin SoundFont. Update these paths according to your installation.

```powershell
$env:VIOLIN_SOUNDFONT = "path-to-project\backend\soundfonts\violin.sf2"

$env:FLUIDSYNTH_PATH = "path-to-fluidsynth\bin\fluidsynth.exe"
```

Replace the example paths with the actual locations on your computer. Make sure both files exist.

### 4. Start the backend server

```powershell
python -m uvicorn main:app --reload --port 8000
```

The backend will run at:

- Application: http://127.0.0.1:8000
- API documentation: http://127.0.0.1:8000/docs

Use the `/convert` endpoint in the API documentation to upload a WAV file and test the conversion.

## How to Run the Frontend

Open a **second terminal** and navigate to the `frontend` directory inside the project folder:

```powershell
cd "path-to-project\frontend"
```

Install the frontend dependencies:

```powershell
npm install
```

Start the development server:

```powershell
npm run dev
```

Open the local URL displayed in the terminal, usually:

http://localhost:5173

Keep both backend and frontend terminals running while using the application.

## How to Use

1. Open the HUM2VIOLIN frontend in your browser.
2. Upload a WAV recording containing humming.
3. Start the conversion.
4. Listen to the generated violin rendition.
5. Download the output WAV file.

## Limitations

- The current version accepts WAV input files.
- Pitch detection may be less accurate with background noise, unclear humming, or rapid pitch changes.
- The generated rendition follows the detected melody and may not reproduce the expressive techniques of a real violinist.
- The current system recreates the melody using instrument synthesis; it does not directly transform the original voice into a natural violin performance.

## Future Enhancements

- Support additional audio formats.
- Add selectable musical keys and major/minor scale options.
- Improve pitch detection and note timing.
- Add more instrument sounds and musical customization options.
- Introduce a visual melody editor and MIDI export.
- Explore AI-based melody continuation and accompaniment generation.

## Conclusion

HUM2VIOLIN demonstrates how audio processing, pitch detection, MIDI generation, and instrument synthesis can work together to turn a human-hummed melody into a violin rendition.
![alt text](mermaid-diagram.png)