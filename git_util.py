from collections import defaultdict
from datetime import datetime, timedelta, timezone
import myframework.myfileio as mf
import os


def git_datetime(date_time):
	tz_beijing = timezone(timedelta(hours=8))
	return datetime.strptime(date_time, "%Y-%m-%dT%H:%M:%S.%f%z").astimezone(tz_beijing).strftime("%Y-%m-%d %H:%M:%S")


def git_week(date_time):
	dt = datetime.strptime(date_time[:10], "%Y-%m-%d")
	weekday = dt.weekday()
	monday = dt - timedelta(days=weekday)
	sunday = monday + timedelta(days=6)
	return f'{monday.strftime("%Y-%m-%d")} ~ {sunday.strftime("%Y-%m-%d")}'


def git_committer(committer):
	return {
		"Neo": "dzr",
  }.get(committer, committer)


def git_html(html_type, results, align=True):
	headers = {
		"detail": ("提交日期", "提交人", "sha", "+", "-", "提交文件", "提交信息"),
		"daily": ("提交日期", "提交人", "提交时间", "sha", "+", "-", "总行数", "文件数", "提交信息"),
		"weekly": ("提交日期", "提交人", "+", "-", "总行数", "提交次数", "文件数")
	}
	classes = {
		"+": ' class="add"',
		"-": ' class="sub"',
		"总行数": ' class="chg"'
	}
	spans = {
		"detail": (0, 1),
		"daily": (0,),
		"weekly": ()
	}

	header = headers[html_type]
	html_th = "<tr><th>" + "</th><th>".join(header) + "</th></tr>"
	html_tr = "<tr>" + "".join([
		"%s" if i in spans[html_type] else f"<td{classes.get(head, '')}>%s</td>"
		for i, head in enumerate(header)
	]) + "</tr>"
	body = "".join([html_tr % tuple(result) for result in results])

	return (
		"<style>"
		"table {font-family:Courier; border-collapse: collapse; font-size: 12px}"
		+ ("table {line-height: 1.2}" if align else "") +
		"td {border: 1px solid; white-space: nowrap}"
		".add {background-color:#aaffaa}"
		".sub {background-color:#ffaaaa}"
		".chg {background-color:#ffff77}"
		"</style>"
		f"<table>{html_th}{body}</table>"
	)


def display_detail():
	if not os.path.exists("git_display"):
		os.mkdir("git_display")
	git_cache = mf.read("git_cache.pkl")

	results = sorted([[
			c["project"], c["datetime"][:10], git_committer(c["committer"]), sha,
			diff["added"], diff["removed"], diff["file"], c["comment"], c["datetime"][11:]
		] for sha, c in git_cache.items() for diff in c["diffs"]
	], key=lambda x: (x[0], x[1], x[2], x[8], x[6]), reverse=True)

	for i in range(len(results) - 1, 0, -1):
		if results[i][3] == results[i - 1][3]:
			for j in range(4, 7):
				results[i - 1][j] = f"{results[i - 1][j]}<br>{results[i][j]}"
			results.pop(i)

	htmls = defaultdict(list)
	spans = [{"date": 1, "committer": 1} for _ in range(len(results))]
	for i in range(len(results) - 1, -1, -1):
		if i and results[i][:2] == results[i - 1][:2]:
			spans[i - 1]["date"] += spans[i]["date"]
			results[i][1] = ""
		else:
			results[i][1] = f'<td rowspan="{spans[i]["date"]}">{results[i][1]}</td>'

		if i and results[i][3] == results[i - 1][3]:
			spans[i - 1]["committer"] += spans[i]["committer"]
			results[i][2] = ""
		else:
			results[i][2] = f'<td rowspan="{spans[i]["committer"]}">{results[i][2]}</td>'

		htmls[results[i][0]].insert(0, results[i][1:-1])

	for project, html in htmls.items():
		mf.write(f"git_display/{project} (detail).html", git_html("detail", html))


def display_daily():
	if not os.path.exists("git_display"):
		os.mkdir("git_display")
	git_cache = mf.read("git_cache.pkl")

	results = sorted([[
		c["project"], c["datetime"][:10], git_committer(c["committer"]), c["datetime"][11:], sha,
		c["additions"], c["deletions"], c["additions"] + c["deletions"], c["change"], c["comment"]
	] for sha, c in git_cache.items()], key=lambda x: (x[0], x[1], x[2], x[3]), reverse=True)

	for i in range(len(results) - 1, 0, -1):
		if results[i][:3] == results[i - 1][:3]:
			for j in range(3, 10):
				results[i - 1][j] = f"{results[i - 1][j]}<br>{results[i][j]}"
			results.pop(i)

	htmls = defaultdict(list)
	spans = [{"date": 1} for _ in range(len(results))]
	for i in range(len(results) - 1, -1, -1):
		if i and results[i][:2] == results[i - 1][:2]:
			spans[i - 1]["date"] += spans[i]["date"]
			results[i][1] = ""
		else:
			results[i][1] = f'<td rowspan="{spans[i]["date"]}">{results[i][1]}</td>'

		htmls[results[i][0]].insert(0, results[i][1:])

	for project, html in htmls.items():
		mf.write(f"git_display/{project} (daily).html", git_html("daily", html))


def display_weekly():
	if not os.path.exists("git_display"):
		os.mkdir("git_display")
	git_cache = mf.read("git_cache.pkl")

	results = defaultdict(lambda: {"additions": 0, "deletions": 0, "times": set(), "change": 0})
	for sha, c in git_cache.items():
		pk = f'{git_week(c["datetime"])},{git_committer(c["committer"])}'
		results[pk]["additions"] += c["additions"]
		results[pk]["deletions"] += c["deletions"]
		results[pk]["times"].add(sha)
		results[pk]["change"] += c["change"]

	results = sorted([pk.split(",") + [
		r["additions"], r["deletions"], r["additions"] + r["deletions"], len(r["times"]), r["change"]
	] for pk, r in results.items()], key=lambda x: (x[0], x[1]), reverse=True)

	for i in range(len(results) - 1, 0, -1):
		if results[i][0] == results[i - 1][0]:
			for j in range(1, 7):
				results[i - 1][j] = f"{results[i - 1][j]}<br>{results[i][j]}"
			results.pop(i)

	mf.write("git_display/weekly.html", git_html("weekly", results))
