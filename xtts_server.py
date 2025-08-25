
import os
import io
import uuid
from typing import Dict

import numpy as np
import soundfile as sf
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel
import traceback

# Coqui TTS
from TTS.api import TTS

# Optional torchaudio for decoding/conversion
try:
	import torch
	import torchaudio
	_TORCHAUDIO = True
except Exception:
	_TORCHAUDIO = False

app = FastAPI(title="XTTS v2 Self-Hosted Server", version="0.1.0")

# Initialize model (first run will download from Hugging Face)
# Allowlist XTTS config classes for PyTorch 2.6+ safe loading
try:
	from torch.serialization import add_safe_globals  # type: ignore
	# Core XTTS config classes
	try:
		from TTS.tts.configs.xtts_config import XttsConfig  # type: ignore
		add_safe_globals([XttsConfig])
	except Exception:
		pass
	try:
		from TTS.tts.models.xtts import XttsAudioConfig  # type: ignore
		add_safe_globals([XttsAudioConfig])
	except Exception:
		pass
	# Shared configs (module path differs by version); import what exists
	for modpath, attr in [
		("TTS.config.shared_configs", "BaseDatasetConfig"),
		("TTS.tts.configs.shared_configs", "BaseDatasetConfig"),
		("TTS.config.shared_configs", "BaseAudioConfig"),
		("TTS.tts.configs.shared_configs", "BaseAudioConfig"),
		("TTS.config.shared_configs", "CharactersConfig"),
		("TTS.tts.configs.shared_configs", "CharactersConfig"),
	]:
		try:
			module = __import__(modpath, fromlist=[attr])
			klass = getattr(module, attr)
			add_safe_globals([klass])
		except Exception:
			pass
except Exception:
	pass

# Force torch.load to use weights_only=False to avoid repeated allowlisting issues
try:
	import torch
	_orig_torch_load = torch.load
	def _patched_torch_load(*args, **kwargs):
		kwargs["weights_only"] = False
		return _orig_torch_load(*args, **kwargs)
	torch.load = _patched_torch_load
except Exception:
	pass

#tts = TTS(model_name="xtts")  # or "xtts_v2.0.2"
tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")

# In-memory voice registry: voice_id -> path to uploaded reference audio
VOICE_DIR = os.path.abspath("voices")
os.makedirs(VOICE_DIR, exist_ok=True)
voice_store: Dict[str, str] = {}


class TTSRequest(BaseModel):
	text: str
	voice_id: str
	language: str | None = "en"


def _normalize_voice_to_wav(src_path: str, dst_path: str, target_sr: int = 24000, max_seconds: float = 10.0) -> str:
	"""If torchaudio is available, decode input audio, crop to max_seconds, convert to mono, resample to target_sr, and write WAV.
	Returns path to WAV (dst_path) on success; otherwise returns original src_path.
	"""
	if not _TORCHAUDIO:
		return src_path
	try:
		waveform, sample_rate = torchaudio.load(src_path)
		# Convert to mono
		if waveform.dim() == 2 and waveform.size(0) > 1:
			waveform = waveform.mean(dim=0, keepdim=True)
		# Crop duration
		max_samples = int(max_seconds * sample_rate)
		if waveform.size(-1) > max_samples:
			waveform = waveform[:, :max_samples]
		# Resample if needed
		if sample_rate != target_sr:
			resampler = torchaudio.transforms.Resample(orig_freq=sample_rate, new_freq=target_sr)
			waveform = resampler(waveform)
		# Write to WAV
		wav_np = waveform.squeeze(0).detach().cpu().numpy()
		with open(dst_path, 'wb') as f:
			sf.write(f, wav_np, target_sr, format='WAV')
		return dst_path
	except Exception:
		print("[voice-normalize] failed:\n" + traceback.format_exc())
		return src_path


@app.post("/clone")
async def clone(audio: UploadFile = File(...)):
	"""Accept a 1–3 minute audio sample, save it, and return a voice_id.
	We keep a normalized 10s mono 24kHz WAV for robust synthesis.
	"""
	voice_id = str(uuid.uuid4())
	orig = audio.filename or "sample.wav"
	_, ext = os.path.splitext(orig)
	if not ext:
		ext = ".wav"
	raw_path = os.path.join(VOICE_DIR, f"{voice_id}{ext}")
	norm_wav_path = os.path.join(VOICE_DIR, f"{voice_id}.wav")
	data = await audio.read()
	with open(raw_path, "wb") as f:
		f.write(data)
	final_path = _normalize_voice_to_wav(raw_path, norm_wav_path)
	voice_store[voice_id] = final_path
	return {"voice_id": voice_id, "voice_path": final_path}


@app.post("/tts")
async def synthesize(req: TTSRequest):
	ref_path = voice_store.get(req.voice_id)
	if not ref_path or not os.path.exists(ref_path):
		return JSONResponse({"error": "invalid voice_id"}, status_code=400)
	# Generate audio with XTTS v2 using the stored reference sample
	try:
		wav = tts.tts(
			text=req.text,
			speaker_wav=ref_path,
			language=req.language or "en",
		)
		buf = io.BytesIO()
		# XTTS typically outputs at 24000 Hz; 22050 is acceptable for playback
		sf.write(buf, np.asarray(wav), 24000, format="WAV")
		return Response(content=buf.getvalue(), media_type="audio/wav")
	except Exception as e:
		print("[synthesis] error:\n" + traceback.format_exc())
		return JSONResponse({"error": f"synthesis failed: {e}"}, status_code=500)


@app.get("/health")
async def health():
	return {"status": "ok", "voices": len(voice_store), "torchaudio": _TORCHAUDIO} 