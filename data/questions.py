from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import json
import os


@dataclass
class Question:
	id: str
	domain: str
	prompt: str
	max_points: int
	keywords: List[str]
	qtype: Optional[str] = None
	params: Optional[Dict[str, Any]] = None

	def score_response(self, user_text: str) -> int:
		if not user_text:
			return 0
		# Default keyword-based scoring; dynamic types are handled by the conversation manager
		text_upper = user_text.upper()
		if not self.keywords:
			return 0
		correct = any(kw.upper() in text_upper for kw in self.keywords)
		return self.max_points if correct else 0


def load_questions() -> List[Question]:
	path = os.path.join(os.path.dirname(__file__), 'questions.json')
	if os.path.exists(path):
		with open(path, 'r', encoding='utf-8') as f:
			raw = json.load(f)
			return [Question(**q) for q in raw]
	return [
		Question(id='orientation_day', domain='orientation', prompt='What day of the week is it today?', max_points=1, keywords=['MONDAY','TUESDAY','WEDNESDAY','THURSDAY','FRIDAY','SATURDAY','SUNDAY']),
		Question(id='orientation_month', domain='orientation', prompt='What month is it?', max_points=1, keywords=['JANUARY','FEBRUARY','MARCH','APRIL','MAY','JUNE','JULY','AUGUST','SEPTEMBER','OCTOBER','NOVEMBER','DECEMBER']),
		Question(id='recent_events', domain='memory', prompt='Name any current event that happened recently.', max_points=1, keywords=['ELECTION','SPORT','NEWS','WEATHER','FESTIVAL']),
		Question(id='attention_math', domain='attention', prompt='Please subtract 7 from 100 and tell me the result.', max_points=1, keywords=['93'], qtype='math_subtract', params={"start_min":90, "start_max":120, "decrement":7}),
	] 