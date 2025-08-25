from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import io
import uuid
from services.conversation import ConversationManager
from services.asr_service import ASRService
from services.xtts_service import XTTSService, XTTSNotConfiguredError
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from services.storage import JSONStore

load_dotenv()


def create_app() -> Flask:
	app = Flask(__name__, static_url_path='/static', static_folder='static')
	CORS(app)

	# Services
	asr_service = ASRService()
	xtts_service = XTTSService()
	conversation_manager = ConversationManager()

	# Persistent stores
	users_store = JSONStore(os.path.join('data', 'users.json'))

	# In-memory session store
	sessions = {}

	def _get_user(user_id: str | None) -> dict | None:
		if not user_id:
			return None
		data = users_store.read()
		return data.get('users', {}).get(user_id)

	def _save_user(user: dict) -> None:
		data = users_store.read()
		users = data.get('users', {})
		users[user['id']] = user
		data['users'] = users
		users_store.write(data)

	@app.get('/health')
	def health():
		return jsonify({
			"status": "ok",
			"xtts_configured": xtts_service.is_configured(),
			"asr_mode": asr_service.mode,
		})

	@app.post('/auth/register')
	def register():
		payload = request.json or {}
		username = (payload.get('username') or '').strip().lower()
		password = payload.get('password') or ''
		if not username or not password:
			return jsonify({"error": "username and password required"}), 400
		data = users_store.read()
		for u in data.get('users', {}).values():
			if u['username'] == username:
				return jsonify({"error": "username exists"}), 409
		user_id = str(uuid.uuid4())
		user = {
			"id": user_id,
			"username": username,
			"password_hash": generate_password_hash(password),
			"voices": [],
			"default_voice_id": None,
		}
		_save_user(user)
		return jsonify({"user_id": user_id})

	@app.post('/auth/login')
	def login():
		payload = request.json or {}
		username = (payload.get('username') or '').strip().lower()
		password = payload.get('password') or ''
		data = users_store.read()
		for u in data.get('users', {}).values():
			if u['username'] == username and check_password_hash(u['password_hash'], password):
				return jsonify({"user_id": u['id'], "default_voice_id": u.get('default_voice_id')})
		return jsonify({"error": "invalid credentials"}), 401

	@app.get('/me')
	def me():
		user_id = request.args.get('user_id')
		u = _get_user(user_id)
		if not u:
			return jsonify({"error": "not found"}), 404
		return jsonify({"id": u['id'], "username": u['username'], "voices": u['voices'], "default_voice_id": u['default_voice_id']})

	@app.post('/voices/name')
	def name_voice():
		payload = request.json or {}
		user_id = payload.get('user_id')
		voice_id = payload.get('voice_id')
		name = (payload.get('name') or '').strip()
		set_default = bool(payload.get('set_default'))
		u = _get_user(user_id)
		if not u:
			return jsonify({"error": "user not found"}), 404
		voices = u.get('voices', [])
		found = False
		for v in voices:
			if v['voice_id'] == voice_id:
				v['name'] = name or v.get('name') or 'My Voice'
				found = True
				break
		if not found:
			voices.append({"voice_id": voice_id, "name": name or 'My Voice'})
		u['voices'] = voices
		if set_default:
			u['default_voice_id'] = voice_id
		_save_user(u)
		return jsonify({"ok": True, "voices": voices, "default_voice_id": u.get('default_voice_id')})

	@app.get('/voices')
	def list_voices():
		user_id = request.args.get('user_id')
		u = _get_user(user_id)
		if not u:
			return jsonify({"error": "user not found"}), 404
		return jsonify({"voices": u.get('voices', []), "default_voice_id": u.get('default_voice_id')})

	@app.post('/voices/select')
	def select_voice():
		payload = request.json or {}
		session_id = payload.get('session_id')
		user_id = payload.get('user_id')
		voice_id = payload.get('voice_id')
		if not session_id or session_id not in sessions:
			return jsonify({"error": "invalid session_id"}), 400
		u = _get_user(user_id)
		if not u:
			return jsonify({"error": "user not found"}), 404
		if voice_id and not any(v['voice_id'] == voice_id for v in u.get('voices', [])):
			return jsonify({"error": "voice not found for user"}), 404
		sessions[session_id]['voice_id'] = voice_id
		return jsonify({"ok": True})

	@app.post('/session')
	def create_session():
		user_id = (request.json or {}).get('user_id') if request.is_json else request.form.get('user_id')
		session_id = str(uuid.uuid4())
		default_voice_id = None
		u = _get_user(user_id)
		if u:
			default_voice_id = u.get('default_voice_id')
		sessions[session_id] = {
			"voice_id": default_voice_id,
			"state": conversation_manager.create_session_state(),
			"user_id": user_id,
		}
		first_prompt = conversation_manager.get_opening_prompt()
		return jsonify({"session_id": session_id, "agent_text": first_prompt, "voice_id": default_voice_id})

	@app.post('/voice/clone')
	def clone_voice():
		session_id = request.form.get('session_id')
		user_id = request.form.get('user_id')
		voice_name = request.form.get('voice_name')
		if 'audio' not in request.files:
			return jsonify({"error": "audio file required (1–3 min)"}), 400
		file = request.files['audio']
		# Persist temp audio
		os.makedirs('uploads', exist_ok=True)
		temp_path = os.path.join('uploads', f"voice_{session_id or uuid.uuid4()}.wav")
		file.save(temp_path)
		try:
			voice_id = xtts_service.clone_voice(temp_path)
			if session_id and session_id in sessions:
				sessions[session_id]['voice_id'] = voice_id
			# attach to user if provided
			if user_id:
				u = _get_user(user_id)
				if u:
					voices = u.get('voices', [])
					voices.append({"voice_id": voice_id, "name": (voice_name or 'My Voice')})
					u['voices'] = voices
					if not u.get('default_voice_id'):
						u['default_voice_id'] = voice_id
					_save_user(u)
			return jsonify({"voice_id": voice_id})
		except XTTSNotConfiguredError as e:
			return jsonify({"error": str(e)}), 503
		except Exception as e:
			return jsonify({"error": f"voice cloning failed: {e}"}), 500

	@app.post('/speak')
	def speak():
		data = request.form or request.json or {}
		session_id = data.get('session_id')
		text = data.get('text')
		if not session_id or session_id not in sessions:
			return jsonify({"error": "invalid session_id"}), 400
		if not text:
			return jsonify({"error": "text is required"}), 400
		voice_id = sessions[session_id]['voice_id']
		if not voice_id:
			return jsonify({"error": "voice not cloned yet"}), 400
		try:
			wav_bytes = xtts_service.synthesize_speech(text=text, voice_id=voice_id)
			return send_file(io.BytesIO(wav_bytes), mimetype='audio/wav', as_attachment=False, download_name='speech.wav')
		except XTTSNotConfiguredError as e:
			return jsonify({"error": str(e)}), 503
		except Exception as e:
			return jsonify({"error": f"tts failed: {e}"}), 500

	@app.post('/asr')
	def asr():
		if 'audio' not in request.files:
			return jsonify({"error": "audio file required"}), 400
		file = request.files['audio']
		orig_name = getattr(file, 'filename', '') or 'input.webm'
		_, ext = os.path.splitext(orig_name)
		if not ext:
			ext = '.webm'
		os.makedirs('uploads', exist_ok=True)
		temp_path = os.path.join('uploads', f"asr_{uuid.uuid4()}{ext}")
		file.save(temp_path)
		try:
			text = asr_service.transcribe(temp_path)
			return jsonify({"text": text})
		except Exception as e:
			return jsonify({"error": f"asr failed: {e}"}), 500
		finally:
			try:
				os.remove(temp_path)
			except Exception:
				pass

	@app.post('/conversation/next')
	def conversation_next():
		payload = request.json or {}
		session_id = payload.get('session_id')
		user_text = payload.get('user_text', '')
		if not session_id or session_id not in sessions:
			return jsonify({"error": "invalid session_id"}), 400
		state = sessions[session_id]['state']
		result = conversation_manager.handle_turn(state=state, user_text=user_text)
		sessions[session_id]['state'] = result['state']
		return jsonify({
			"agent_text": result['agent_text'],
			"phase": result['phase'],
			"scores": result['scores'],
			"done": result['done'],
		})

	@app.get('/')
	def index():
		return app.send_static_file('index.html')

	return app


app = create_app()

if __name__ == '__main__':
	app.run(host='0.0.0.0', port=int(os.getenv('PORT', '5000')), debug=True) 