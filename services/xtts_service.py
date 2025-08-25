import os
import requests
from typing import Optional


class XTTSNotConfiguredError(Exception):
	pass


class XTTSService:
	"""Wrapper around a self-hosted XTTS v2 (or equivalent) HTTP service.

	Environment variables:
	- XTTS_BASE_URL: Base URL of the self-hosted XTTS service
		Expected endpoints:
			POST {XTTS_BASE_URL}/clone -> form-data: audio(file)
			  Response: {"voice_id": str}
			POST {XTTS_BASE_URL}/tts -> json: {"text": str, "voice_id": str}
			  Response: audio/wav bytes
	"""

	def __init__(self) -> None:
		self.base_url: Optional[str] = os.getenv('XTTS_BASE_URL')

	def is_configured(self) -> bool:
		return bool(self.base_url)

	def _require_configured(self) -> None:
		if not self.base_url:
			raise XTTSNotConfiguredError("XTTS_BASE_URL not set. Configure self-hosted XTTS service.")

	def clone_voice(self, audio_path: str) -> str:
		self._require_configured()
		with open(audio_path, 'rb') as f:
			resp = requests.post(f"{self.base_url}/clone", files={'audio': f}, timeout=120)
			resp.raise_for_status()
			data = resp.json()
			voice_id = data.get('voice_id')
			if not voice_id:
				raise RuntimeError('XTTS clone did not return voice_id')
			return voice_id

	def synthesize_speech(self, text: str, voice_id: str) -> bytes:
		self._require_configured()
		resp = requests.post(
			f"{self.base_url}/tts",
			json={"text": text, "voice_id": voice_id},
			timeout=120
		)
		resp.raise_for_status()
		return resp.content 