import json
import re
import sys
from pathlib import Path

try:
	import pdfplumber
except Exception as e:
	print("Install pdfplumber: pip install pdfplumber")
	raise

PDF_PATH = Path('Ques for Granular Testing.pdf')
OUT_PATH = Path('data/questions.json')

# Very rough heuristic parser; manual review recommended
QUESTION_PAT = re.compile(r"^\s*(\d+)[\).:\-\s]+(.+?)\s*$")


def parse_pdf(pdf_path: Path):
	texts = []
	with pdfplumber.open(str(pdf_path)) as pdf:
		for page in pdf.pages:
			texts.append(page.extract_text() or '')
	full = '\n'.join(texts)
	lines = [ln for ln in full.splitlines() if ln.strip()]
	questions = []
	qid = 1
	for ln in lines:
		m = QUESTION_PAT.match(ln)
		if m:
			prompt = m.group(2).strip()
			questions.append({
				"id": f"q{qid}",
				"domain": "general",
				"prompt": prompt,
				"max_points": 1,
				"keywords": []
			})
			qid += 1
	return questions


def main():
	qs = parse_pdf(PDF_PATH)
	if not qs:
		print("No questions parsed. Adjust parser.")
		return
	OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
	with open(OUT_PATH, 'w', encoding='utf-8') as f:
		json.dump(qs, f, ensure_ascii=False, indent=2)
	print(f"Wrote {len(qs)} questions to {OUT_PATH}")


if __name__ == '__main__':
	main() 