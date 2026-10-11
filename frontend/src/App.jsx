import { useEffect, useRef, useState } from "react";
import "./App.css";

const API = "http://127.0.0.1:8000";

function encodeWav(audioBuffer) {
  const channels = audioBuffer.numberOfChannels;
  const length = audioBuffer.length;
  const sampleRate = audioBuffer.sampleRate;

  const samples = new Float32Array(length);

  for (let c = 0; c < channels; c++) {
    const channel = audioBuffer.getChannelData(c);
    for (let i = 0; i < length; i++) {
      samples[i] += channel[i] / channels;
    }
  }

  const buffer = new ArrayBuffer(44 + length * 2);
  const view = new DataView(buffer);

  function writeString(offset, text) {
    for (let i = 0; i < text.length; i++) {
      view.setUint8(offset + i, text.charCodeAt(i));
    }
  }

  writeString(0, "RIFF");
  view.setUint32(4, 36 + length * 2, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(36, "data");
  view.setUint32(40, length * 2, true);

  for (let i = 0; i < length; i++) {
    const sample = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(
      44 + i * 2,
      sample < 0 ? sample * 32768 : sample * 32767,
      true
    );
  }

  return new Blob([buffer], { type: "audio/wav" });
}

export default function App() {
  const [file, setFile] = useState(null);
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [output, setOutput] = useState("");

  const recorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((track) => track.stop());
      if (output) URL.revokeObjectURL(output);
    };
  }, [output]);

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });

      streamRef.current = stream;
      chunksRef.current = [];

      const recorder = new MediaRecorder(stream);
      recorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        try {
          const recordingBlob = new Blob(chunksRef.current, {
            type: recorder.mimeType,
          });

          const context = new AudioContext();

          try {
            const bytes = await recordingBlob.arrayBuffer();
            const decoded = await context.decodeAudioData(bytes);
            const wav = encodeWav(decoded);

            setFile(
              new File([wav], "my-humming.wav", {
                type: "audio/wav",
              })
            );
            setMessage("Recording ready for conversion.");
          } finally {
            await context.close();
          }
        } catch {
          setMessage("Could not process the recording. Please try again.");
        } finally {
          stream.getTracks().forEach((track) => track.stop());
          streamRef.current = null;
        }
      };

      recorder.start();
      setRecording(true);
      setMessage("Recording your humming...");
    } catch {
      setMessage("Microphone access failed. Check browser permissions.");
    }
  }

  function stopRecording() {
    if (recorderRef.current?.state === "recording") {
      recorderRef.current.stop();
      setRecording(false);
    }
  }

  async function convert() {
    if (!file) {
      setMessage("Upload a WAV file or record your humming first.");
      return;
    }

    setBusy(true);
    setMessage("Analyzing melody and generating violin audio...");

    try {
      const form = new FormData();
      form.append("file", file);

      const response = await fetch(`${API}/convert`, {
        method: "POST",
        body: form,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Conversion failed.");
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);

      setOutput((previous) => {
        if (previous) URL.revokeObjectURL(previous);
        return url;
      });

      setMessage("Your violin recording is ready!");
    } catch (error) {
      setMessage(error.message || "Could not connect to the backend.");
    } finally {
      setBusy(false);
    }
  }

  const activeStep = output ? 3 : file ? 2 : 1;

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="brand">
          <div className="brand-mark">♫</div>
          <div className="brand-text">
            <span className="brand-name">HUM2VIOLIN</span>
            <span className="brand-sub">Melody synthesis studio</span>
          </div>
        </div>

        <nav className="step-nav">
          <div className={`step ${activeStep >= 1 ? "done" : ""} ${activeStep === 1 ? "active" : ""}`}>
            <span className="step-index">01</span>
            <div className="step-copy">
              <span className="step-title">Source</span>
              <span className="step-desc">Upload or hum</span>
            </div>
          </div>
          <div className={`step ${activeStep >= 2 ? "done" : ""} ${activeStep === 2 ? "active" : ""}`}>
            <span className="step-index">02</span>
            <div className="step-copy">
              <span className="step-title">Convert</span>
              <span className="step-desc">Generate violin</span>
            </div>
          </div>
          <div className={`step ${activeStep >= 3 ? "done" : ""} ${activeStep === 3 ? "active" : ""}`}>
            <span className="step-index">03</span>
            <div className="step-copy">
              <span className="step-title">Result</span>
              <span className="step-desc">Preview & export</span>
            </div>
          </div>
        </nav>

        <div className="sidebar-footer">
          <p className="sidebar-note">
            All audio is processed locally or via your own backend.
          </p>
        </div>
      </aside>

      <main className="app-main">
        <header className="page-header">
          <div>
            <h1>Turn a hum into a violin</h1>
            <p className="page-sub">
              Record your melody or drop a WAV file. We'll handle the rest.
            </p>
          </div>
        </header>

        <div className="workspace">
          <section className="workspace-col">
            <div className="card">
              <div className="card-head">
                <h2>Source audio</h2>
                <span className="card-tag">Step 01</span>
              </div>

              <label className="dropzone">
                <input
                  type="file"
                  accept=".wav,audio/wav"
                  onChange={(e) => {
                    setFile(e.target.files?.[0] || null);
                    setMessage("");
                  }}
                />
                <div className="dropzone-icon">↑</div>
                <div className="dropzone-copy">
                  <span className="dropzone-title">Choose a WAV file</span>
                  <span className="dropzone-hint">or drag and drop it here</span>
                </div>
              </label>

              <div className="file-chip">
                <span className="file-chip-label">Selected</span>
                <span className={`file-chip-value ${file ? "has-file" : ""}`}>
                  {file ? file.name : "No file selected"}
                </span>
              </div>

              <div className="divider">
                <span>or</span>
              </div>

              <div className="record-row">
                {!recording ? (
                  <button
                    onClick={startRecording}
                    disabled={busy}
                    className="btn btn-ghost"
                  >
                    <span className="rec-dot" />
                    Record humming
                  </button>
                ) : (
                  <button
                    onClick={stopRecording}
                    className="btn btn-danger"
                  >
                    <span className="rec-square" />
                    Stop recording
                  </button>
                )}
                {recording && (
                  <div className="rec-indicator">
                    <span className="rec-pulse" />
                    Live
                  </div>
                )}
              </div>
            </div>

            <div className="card">
              <div className="card-head">
                <h2>Convert to violin</h2>
                <span className="card-tag">Step 02</span>
              </div>
              <p className="card-desc">
                Once your audio is ready, generate the violin version.
              </p>
              <button
                className="btn btn-primary btn-block"
                onClick={convert}
                disabled={busy || recording || !file}
              >
                {busy ? (
                  <>
                    <span className="spinner" />
                    Processing…
                  </>
                ) : (
                  <>
                    Transform into violin
                    <span className="arrow">→</span>
                  </>
                )}
              </button>

              {message && (
                <div className="status" role="status">
                  <span className="status-dot" />
                  {message}
                </div>
              )}
            </div>
          </section>

          <section className="workspace-col">
            <div className={`card result-card ${output ? "ready" : ""}`}>
              <div className="card-head">
                <h2>Result</h2>
                <span className="card-tag">Step 03</span>
              </div>

              {!output ? (
                <div className="empty-state">
                  <div className="empty-icon">🎻</div>
                  <p className="empty-title">No violin audio yet</p>
                  <p className="empty-sub">
                    Convert your humming or file to see the result here.
                  </p>
                </div>
              ) : (
                <div className="result-body">
                  <audio controls src={output} />
                  <a
                    href={output}
                    download="hum2violin.wav"
                    className="btn btn-primary btn-block"
                  >
                    ↓ Download violin audio
                  </a>
                </div>
              )}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}