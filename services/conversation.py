from typing import Dict, List, Literal, Tuple
from services.scoring import ScoringEngine
from data.questions import Question, load_questions
import random
import re

Phase = Literal['greeting', 'registration_present', 'registration_repeat', 'intervening', 'delayed_recall', 'summary', 'done']


class ConversationManager:
	def __init__(self) -> None:
		self.questions: List[Question] = load_questions()

	def create_session_state(self) -> Dict:
		return {
			"phase": 'greeting',
			"registration_words": [],
			"user_repeated_words": [],
			"intervening_idx": 0,
			"delayed_recall_attempt": [],
			"scoring": ScoringEngine(),
			"dynamic": {},
		}

	def get_opening_prompt(self) -> str:
		return "Hello, I’m your assistant. We’ll do a short memory and thinking check. Ready to begin?"

	def handle_turn(self, state: Dict, user_text: str) -> Dict:
		phase: Phase = state["phase"]
		if phase == 'greeting':
			return self._do_registration_present(state)
		if phase == 'registration_present':
			return self._do_registration_repeat(state, user_text)
		if phase == 'registration_repeat':
			return self._do_intervening(state, user_text)
		if phase == 'intervening':
			return self._do_intervening(state, user_text)
		if phase == 'delayed_recall':
			return self._do_delayed_recall(state, user_text)
		if phase == 'summary':
			return self._do_summary(state)
		return {"state": state, "agent_text": "", "phase": 'done', "scores": state['scoring'].snapshot(), "done": True}

	def _choose_registration_words(self) -> List[str]:
		return ["APPLE", "TABLE", "PENNY"]

	def _parse_words(self, text: str) -> List[str]:
		return [w.strip().upper() for w in text.replace(',', ' ').split() if w.strip()]

	def _do_registration_present(self, state: Dict) -> Dict:
		words = self._choose_registration_words()
		state["registration_words"] = words
		state["phase"] = 'registration_present'
		agent = f"Please remember these three words: {', '.join(words)}. Now, please repeat them back to me."
		return {"state": state, "agent_text": agent, "phase": state['phase'], "scores": state['scoring'].snapshot(), "done": False}

	def _do_registration_repeat(self, state: Dict, user_text: str) -> Dict:
		user_words = self._parse_words(user_text)
		state["user_repeated_words"] = user_words
		correct = sum(1 for w in state['registration_words'] if w in user_words)
		state['scoring'].add_three_word_registration(correct)
		state['phase'] = 'intervening'
		return self._prompt_next_intervening(state)

	def _generate_dynamic_prompt(self, q: Question, state: Dict) -> str:
		if q.qtype == 'math_subtract':
			params = q.params or {}
			start_min = int(params.get('start_min', 90))
			start_max = int(params.get('start_max', 120))
			decrement = int(params.get('decrement', 7))
			start = random.randint(start_min, start_max)
			state['dynamic']['math'] = {"start": start, "decrement": decrement, "answer": start - decrement}
			return f"Please subtract {decrement} from {start} and tell me the result."
		if q.qtype == 'math_add':
			params = q.params or {}
			a = int(params.get('a', 0))
			b = int(params.get('b', 0))
			state['dynamic']['math_add'] = {"a": a, "b": b, "answer": a + b}
			return q.prompt
		return q.prompt

	def _score_dynamic_answer(self, q: Question, state: Dict, user_text: str) -> int:
		if q.qtype == 'math_subtract':
			cfg = state.get('dynamic', {}).get('math', {})
			try:
				expected = int(cfg.get('answer', 0))
				m = re.search(r"-?\d+", user_text)
				if m and int(m.group(0)) == expected:
					return q.max_points
			except Exception:
				return 0
		if q.qtype == 'math_add':
			cfg = state.get('dynamic', {}).get('math_add', {})
			try:
				expected = int(cfg.get('answer', 0))
				m = re.search(r"-?\d+", user_text)
				if m and int(m.group(0)) == expected:
					return q.max_points
				return 0
			except Exception:
				return 0
		if q.qtype == 'repeat_digits':
			params = q.params or {}
			expected = [str(d) for d in params.get('sequence', [])]
			spoken = [tok for tok in re.findall(r"\d+", user_text)]
			# score equals count of expected digits present in any order, up to max_points
			correct = sum(1 for d in expected if d in spoken)
			return min(correct, q.max_points)
		if q.qtype == 'yes_no':
			val = user_text.strip().lower()
			is_yes = any(w in val for w in ["yes", "yeah", "yep", "ya", "sure"]) and not any(w in val for w in ["no", "nope"])
			expected_yes = str((q.params or {}).get('expected', 'yes')).lower() in ['yes', 'true', '1']
			return q.max_points if (is_yes == expected_yes) else 0
		if q.qtype == 'free_speech_min_words':
			min_words = int((q.params or {}).get('min_words', 5))
			count = len([w for w in re.findall(r"\w+", user_text)])
			return q.max_points if count >= min_words else 0
		if q.qtype == 'planning_keywords':
			keywords = [str(k).upper() for k in (q.params or {}).get('keywords', [])]
			text_upper = user_text.upper()
			count = sum(1 for k in keywords if k in text_upper)
			return min(count, q.max_points)
		return q.score_response(user_text)

	def _prompt_next_intervening(self, state: Dict) -> Dict:
		i = state['intervening_idx']
		if i >= len(self.questions):
			state['phase'] = 'delayed_recall'
			return {"state": state, "agent_text": "Now, please tell me the three words I asked you to remember.", "phase": state['phase'], "scores": state['scoring'].snapshot(), "done": False}
		q = self.questions[i]
		prompt = self._generate_dynamic_prompt(q, state)
		return {"state": state, "agent_text": prompt, "phase": state['phase'], "scores": state['scoring'].snapshot(), "done": False}

	def _do_intervening(self, state: Dict, user_text: str) -> Dict:
		i = state['intervening_idx']
		if i < len(self.questions):
			q = self.questions[i]
			points = self._score_dynamic_answer(q, state, user_text)
			state['scoring'].add_score(q.domain, points, q.max_points)
			state['intervening_idx'] = i + 1
		return self._prompt_next_intervening(state)

	def _do_delayed_recall(self, state: Dict, user_text: str) -> Dict:
		user_words = self._parse_words(user_text)
		state['delayed_recall_attempt'] = user_words
		correct = sum(1 for w in state['registration_words'] if w in user_words)
		state['scoring'].add_three_word_recall(correct)
		state['phase'] = 'summary'
		return self._do_summary(state)

	def _do_summary(self, state: Dict) -> Dict:
		snapshot = state['scoring'].snapshot()
		state['phase'] = 'done'
		agent = "Thanks for completing the check. Here is a quick summary of your results."
		return {"state": state, "agent_text": agent, "phase": 'summary', "scores": snapshot, "done": True} 