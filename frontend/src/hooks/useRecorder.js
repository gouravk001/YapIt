import { useEffect, useRef, useState } from "react";

export function useRecorder(onStopCallback) {
  const [isRecording, setIsRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [analyser, setAnalyser] = useState(null);
  const [error, setError] = useState(null);
  const [lastBlob, setLastBlob] = useState(null);
  const [lastCapturedAt, setLastCapturedAt] = useState(null);

  const recorderRef = useRef(null);
  const chunksRef = useRef([]);
  const audioCtxRef = useRef(null);
  const timerRef = useRef(null);
  const streamRef = useRef(null);
  const capturedAtRef = useRef(null);

  useEffect(() => {
    return () => {
      clearInterval(timerRef.current);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
      if (audioCtxRef.current && audioCtxRef.current.state !== "closed") {
        audioCtxRef.current.close().catch(() => {});
      }
    };
  }, []);

  const startRecording = async () => {
    setError(null);
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error("Audio recording is not supported in this browser.");
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      audioCtxRef.current = ctx;
      const source = ctx.createMediaStreamSource(stream);
      const an = ctx.createAnalyser();
      an.fftSize = 256;
      source.connect(an);
      setAnalyser(an);

      const mimeTypes = [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/ogg;codecs=opus",
        "audio/mp4",
      ];
      const supportedType = mimeTypes.find((t) => MediaRecorder.isTypeSupported(t));
      const options = supportedType ? { mimeType: supportedType } : {};

      const recorder = new MediaRecorder(stream, options);
      recorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      recorder.onstop = () => {
        const mime = recorder.mimeType || "audio/webm";
        const blob = new Blob(chunksRef.current, { type: mime });
        setLastBlob(blob);

        if (streamRef.current) {
          streamRef.current.getTracks().forEach((t) => t.stop());
          streamRef.current = null;
        }
        if (audioCtxRef.current && audioCtxRef.current.state !== "closed") {
          audioCtxRef.current.close().catch(() => {});
          audioCtxRef.current = null;
        }
        setAnalyser(null);

        const captured = capturedAtRef.current || new Date().toISOString();
        if (onStopCallback) {
          onStopCallback(blob, captured);
        }
      };

      recorder.start(100);
      const captured = new Date().toISOString();
      capturedAtRef.current = captured;
      setLastCapturedAt(captured);

      setSeconds(0);
      setIsRecording(true);

      clearInterval(timerRef.current);
      timerRef.current = setInterval(() => {
        setSeconds((s) => s + 1);
      }, 1000);
    } catch (err) {
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        setError("Microphone permission was denied. Please allow microphone access.");
      } else if (err.name === "NotFoundError") {
        setError("No microphone device found.");
      } else {
        setError(err.message || "Failed to start audio recording.");
      }
      setIsRecording(false);
    }
  };

  const stopRecording = () => {
    clearInterval(timerRef.current);
    if (recorderRef.current && recorderRef.current.state !== "inactive") {
      recorderRef.current.stop();
    }
    setIsRecording(false);
  };

  return {
    isRecording,
    analyser,
    seconds,
    startRecording,
    stopRecording,
    lastBlob,
    lastCapturedAt,
    error,
    setError,
  };
}

