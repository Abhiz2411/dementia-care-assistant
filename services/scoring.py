from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass
class DomainScore:
	scored_points: int = 0
	max_points: int = 0

	def add(self, points: int, max_points: int) -> None:
		self.scored_points += max(0, points)
		self.max_points += max(0, max_points)

	@property
	def percent(self) -> float:
		if self.max_points == 0:
			return 0.0
		return (self.scored_points / self.max_points) * 100.0

	@property
	def category(self) -> str:
		p = self.percent
		if p >= 85:
			return 'Excellent'
		if p >= 70:
			return 'Good'
		if p >= 50:
			return 'Fair'
		return 'Needs Attention'


@dataclass
class ScoringEngine:
	domains: Dict[str, DomainScore] = field(default_factory=dict)

	def add_score(self, domain: str, points: int, max_points: int) -> None:
		if domain not in self.domains:
			self.domains[domain] = DomainScore()
		self.domains[domain].add(points, max_points)

	def add_three_word_registration(self, correct: int) -> None:
		self.add_score('three_word_registration', correct, 3)

	def add_three_word_recall(self, correct: int) -> None:
		self.add_score('delayed_recall', correct, 3)

	def snapshot(self) -> Dict[str, Dict[str, float | int | str]]:
		out: Dict[str, Dict[str, float | int | str]] = {}
		for domain, score in self.domains.items():
			out[domain] = {
				"points": score.scored_points,
				"max_points": score.max_points,
				"percent": round(score.percent, 2),
				"category": score.category,
			}
		# overall
		total_points, total_max = self._overall()
		out['overall'] = {
			"points": total_points,
			"max_points": total_max,
			"percent": round((total_points / total_max) * 100.0, 2) if total_max else 0.0,
			"category": self._category(total_points, total_max),
		}
		return out

	def _overall(self) -> Tuple[int, int]:
		total_points = sum(d.scored_points for d in self.domains.values())
		total_max = sum(d.max_points for d in self.domains.values())
		return total_points, total_max

	def _category(self, points: int, max_points: int) -> str:
		if max_points == 0:
			return 'Needs Attention'
		percent = (points / max_points) * 100.0
		if percent >= 85:
			return 'Excellent'
		if percent >= 70:
			return 'Good'
		if percent >= 50:
			return 'Fair'
		return 'Needs Attention' 