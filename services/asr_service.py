import os
from typing import Literal

try:
	import google.generativeai as genai  # type: ignore
	_GOOGLE_AVAILABLE = True
except Exception:
	_GOOGLE_AVAILABLE = False


class ASRService:
	"""ASR abstraction. Uses Gemini Audio Transcription if GOOGLE_API_KEY is set; otherwise returns a stub.

	Expected models: "gemini-1.5-flash" with audio transcription via content parts.
	"""

	def __init__(self) -> None:
		self.mode: Literal['gemini', 'stub'] = 'stub'
		api_key = os.getenv('GOOGLE_API_KEY')
		if api_key and _GOOGLE_AVAILABLE:
			genai.configure(api_key=api_key)
			self.mode = 'gemini'

	def transcribe(self, audio_path: str) -> str:
		if self.mode == 'gemini':
			model_name = os.getenv('GEMINI_ASR_MODEL', 'gemini-1.5-flash')
			model = genai.GenerativeModel(model_name)
			# Build content with audio file reference
			mime = _guess_mime(audio_path)
			try:
				with open(audio_path, 'rb') as f:
					audio_bytes = f.read()
				parts = [
					{"text": "Transcribe the following audio to plain text."},
					{"inline_data": {"mime_type": mime, "data": audio_bytes}},
				]
				resp = model.generate_content(parts)
				text = getattr(resp, 'text', '') or ''
				return text.strip()
			except Exception:
				return ""
		# Fallback stub if Gemini is not configured
		return ""


def _guess_mime(path: str) -> str:
	p = path.lower()
	if p.endswith('.wav'): return 'audio/wav'
	if p.endswith('.mp3'): return 'audio/mpeg'
	if p.endswith('.m4a'): return 'audio/mp4'
	if p.endswith('.webm'): return 'audio/webm'
	return 'application/octet-stream' 