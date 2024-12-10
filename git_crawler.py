from git_util import *
from itertools import chain
from git_config import *
import json
import math
import myframework.mycrawler as mc


def git_commit():
	if not os.path.exists("git_cache.pkl"):
		mf.write("git_cache.pkl", {})
	git_cache = mf.read("git_cache.pkl")

	comments = ("Merge branch", "Merge remote-tracking branch", "Merge pull request", "Revert")
	for domain, p in PROJECT.items():
		urls = [p["url"]["change"].split("%s")[0] + name for name in p["id"]]
		datas = mc.crawl(urls, cookie=p["cookie"], sifters=["project-stat-value.+?<"])
		pages = {
			urls[i].split("/")[-1]: math.ceil(int(data[0][20:-1].replace(",", "")) / 100)
			for i, data in enumerate(datas)
		}

		for name, project_id in p["id"].items():
			urls = [p["url"]["commit"] % (project_id, i + 1) for i in range(pages[name])]
			datas = mc.crawl(urls, cookie=p["cookie"])

			for d in chain.from_iterable(json.loads(data) for data in datas):
				if any(d["title"].startswith(comment) for comment in comments):
					continue
				if d["short_id"] in git_cache:
					continue
				git_cache[d["short_id"]] = {
					"project": f"[{domain}] {name}",
					"datetime": git_datetime(d["committed_date"]),
					"committer": d["author_name"],
					"comment": d["title"],
				}
			mf.write("git_cache.pkl", git_cache)


def git_diff():
	git_cache = mf.read("git_cache.pkl")

	domain_urls = defaultdict(list)
	for sha, c in git_cache.items():
		if "additions" in c and "deletions" in c:
			continue
		domain, name = c["project"].split(" ", 1)
		domain = domain[1:-1]
		project_id = PROJECT[domain]["id"][name]
		domain_urls[domain].append(PROJECT[domain]["url"]["diff"] % (project_id, sha))

	for domain, urls in domain_urls.items():
		datas = mc.crawl(urls, cookie=PROJECT[domain]["cookie"])
		for i, data in enumerate(datas):
			sha = urls[i].split("/")[-1]
			stats = json.loads(data)["stats"]
			git_cache[sha].update({"additions": stats["additions"], "deletions": stats["deletions"]})
		mf.write("git_cache.pkl", git_cache)


def git_change():
	git_cache = mf.read("git_cache.pkl")

	domain_urls = defaultdict(list)
	for sha, c in git_cache.items():
		if "change" in c and "diffs" in c:
			continue
		domain, name = c["project"].split(" ", 1)
		domain = domain[1:-1]
		domain_urls[domain].append(PROJECT[domain]["url"]["change"] % (name, sha))
		if len(domain_urls[domain]) >= 2000:
			break

	sifters = ["data-files.+?</div>", "gl-tab-counter-badge.+?<"]
	for domain, urls in domain_urls.items():
		datas = mc.crawl(urls, cookie=PROJECT[domain]["cookie"], sifters=sifters)
		for i, data in enumerate(datas):
			sha = urls[i].split("/")[-1]
			diffs = eval(data[0][12:-8].replace("&quot;", '"'))
			change = int(data[1][22:-1])
			git_cache[sha].update({
				"change": change,
				"diffs": [{"added": diff["added"], "removed": diff["removed"], "file": diff["name"]} for diff in diffs]
			})
		mf.write("git_cache.pkl", git_cache)


if __name__ == "__main__":
	git_commit()
	git_diff()
	git_change()

	display_detail()
	display_daily()
	display_weekly()
