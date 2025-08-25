import json
import os
import threading
from typing import Any, Dict


class JSONStore:
	def __init__(self, path: str) -> None:
		self.path = path
		self._lock = threading.Lock()
		os.makedirs(os.path.dirname(path), exist_ok=True)
		if not os.path.exists(self.path):
			with open(self.path, 'w', encoding='utf-8') as f:
				f.write('{}')

	def read(self) -> Dict[str, Any]:
		with self._lock:
			try:
				with open(self.path, 'r', encoding='utf-8') as f:
					return json.load(f)
			except Exception:
				return {}

	def write(self, data: Dict[str, Any]) -> None:
		with self._lock:
			with open(self.path, 'w', encoding='utf-8') as f:
				json.dump(data, f, ensure_ascii=False, indent=2) 