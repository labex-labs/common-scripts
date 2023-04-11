import re
import json
import requests
import argparse


class Feishu:
    """Feishu API"""

    def __init__(self, app_id: str, app_secret: str) -> None:
        self.app_id = app_id
        self.app_secret = app_secret

    def tenant_access_token(self):
        """Get tenant access token"""
        r = requests.post(
            url="https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            headers={
                "Content-Type": "application/json; charset=utf-8",
            },
            data=json.dumps({"app_id": self.app_id, "app_secret": self.app_secret}),
        )
        return r.json()["tenant_access_token"]

    def get_bitable_records(self, app_token: str, table_id: str, params: str) -> None:
        """Get bitable records"""
        records = []
        r = requests.get(
            url=f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records?{params}",
            headers={
                "Authorization": f"Bearer {self.tenant_access_token()}",
            },
        )
        if r.json()["data"]["total"] > 0:
            records += r.json()["data"]["items"]
            # 当存在多页时，递归获取
            while r.json()["data"]["has_more"]:
                page_token = r.json()["data"]["page_token"]
                r = requests.get(
                    url=f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records?page_token={page_token}&{params}",
                    headers={
                        "Authorization": f"Bearer {self.tenant_access_token()}",
                    },
                )
                if r.json()["data"]["total"] > 0:
                    records += r.json()["data"]["items"]
        return records

    def add_bitable_record(self, app_token: str, table_id: str, data: dict) -> None:
        """Add record to bitable"""
        r = requests.post(
            url=f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records",
            headers={
                "Authorization": f"Bearer {self.tenant_access_token()}",
                "Content-Type": "application/json; charset=utf-8",
            },
            data=json.dumps(data),
        )
        return r.json()

    def update_bitable_record(
        self, app_token: str, table_id: str, record_id: str, data: dict
    ) -> None:
        """Update record in bitable"""
        r = requests.put(
            url=f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}",
            headers={
                "Authorization": f"Bearer {self.tenant_access_token()}",
                "Content-Type": "application/json; charset=utf-8",
            },
            data=json.dumps(data),
        )
        return r.json()

    def delete_bitable_record(
        self, app_token: str, table_id: str, record_id: str
    ) -> None:
        """Delete record in bitable"""
        r = requests.delete(
            url=f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}",
            headers={
                "Authorization": f"Bearer {self.tenant_access_token()}",
                "Content-Type": "application/json; charset=utf-8",
            },
        )
        return r.json()


class GitHub:
    """GitHub 相关 API"""

    def __init__(self, token: str) -> None:
        self.token = token

    def get_pr_list(self, repo_name: str) -> list:
        """获取 pr 列表

        Args:
            repo_name (str): 仓库名称
        """
        url = f"https://api.github.com/repos/{repo_name}/pulls"
        headers = {
            "Authorization": "token " + self.token,
            "Accept": "application/vnd.github+json",
        }
        params = {
            "state": "all",
            "per_page": 100,
        }

        all_pulls = []
        page = 1

        while True:
            params["page"] = page
            print(f"Fetching page {page} of pulls...")
            response = requests.get(url, headers=headers, params=params)
            if response.status_code != 200:
                raise Exception(
                    f"Error retrieving pulls: {response.status_code}, {response.text}"
                )

            pulls = response.json()
            if not pulls:
                break

            all_pulls.extend(pulls)
            page += 1

        # 仅保留 open 和 merged 状态的 PR
        only_pulls = [
            pull
            for pull in all_pulls
            if pull["state"] == "open" or pull.get("merged_at") is not None
        ]
        return only_pulls


class Sync:
    def __init__(self, app_id: str, app_secret: str, ghtoken: str) -> None:
        self.ghtoken = ghtoken
        self.github = GitHub(token=ghtoken)
        self.feishu = Feishu(app_id, app_secret)
        self.app_token = "bascnNz4Nqjqgqm1Nm5AYke6xxb"
        self.table_id = "tblExqBjw46rHCre"

    def pr_index_json(self, repo_name: str, pr_number: int) -> list:
        url = f"https://api.github.com/repos/{repo_name}/pulls/{pr_number}/files"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": "token " + self.ghtoken,
        }
        response = requests.get(url, headers=headers)
        raw_urls = []
        for file in response.json():
            if "index.json" in file["filename"]:
                raw_url = file["raw_url"]
                filename = file["filename"]
                raw_urls.append(
                    {
                        "raw_url": raw_url,
                        "filename": filename,
                    }
                )
        if len(raw_urls) == 1:
            print(f"Found {len(raw_urls)} index.json in PR {pr_number}.")
            index_json = requests.get(raw_urls[0]["raw_url"]).json()
            lab_slug = raw_urls[0]["filename"].removesuffix("/index.json")
            return index_json, lab_slug
        else:
            return None, None

    def pr_reviews(self, repo_name: str, pr_number: int) -> list:
        url = f"https://api.github.com/repos/{repo_name}/pulls/{pr_number}/reviews"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": "token " + self.ghtoken,
        }
        response = requests.get(url, headers=headers)
        approved_by = []
        changes_requested_by = []
        for review in response.json():
            if review["state"] == "APPROVED":
                approved_by.append(review["user"]["login"])
            elif review["state"] == "CHANGES_REQUESTED":
                changes_requested_by.append(review["user"]["login"])
        return list(set(approved_by)), list(set(changes_requested_by))

    def sync_pr(self, repo_name: str) -> None:
        # Get all records from feishu
        records = self.feishu.get_bitable_records(
            self.app_token, self.table_id, params=""
        )
        # Make a dict of PR_TITLE and record_id
        records_dicts = {r["fields"]["SCENARIO_SLUG"]: r["record_id"] for r in records}
        # Get all pr from github
        pr_list = self.github.get_pr_list(repo_name)
        print(f"Found {len(pr_list)} pr in GitHub.")
        for pr in pr_list:
            try:
                # parse index.json
                pr_number = pr["number"]
                index_json, lab_slug = self.pr_index_json(repo_name, pr_number)
                if index_json != None:
                    lab_title = index_json.get("title")
                    lab_type = index_json.get("type")
                    pr_title = pr["title"]
                    pr_state = pr["state"]
                    pr_user = pr["user"]["login"]
                    pr_html_url = pr["html_url"]
                    # assignees
                    assignees = pr["assignees"]
                    if len(assignees) == 0:
                        assignees = []
                    else:
                        assignees = [a["login"] for a in assignees]
                    # labels
                    pr_labels = pr["labels"]
                    if len(pr_labels) == 0:
                        pr_labels = []
                    else:
                        pr_labels = [l["name"] for l in pr_labels]
                    # milestone
                    milestone = pr.get("milestone")
                    if milestone != None:
                        milestone = pr.get("milestone").get("title")
                    # MERGED_BY
                    merged_by = pr.get("merged_by")
                    # pr_reviews
                    approved_by, changes_requested_by = self.pr_reviews(
                        repo_name, pr_number
                    )
                    # payloads
                    payloads = {
                        "fields": {
                            "SCENARIO_TITLE": lab_title,
                            "SCENARIO_SLUG": lab_slug,
                            "SCENARIO_TYPE": lab_type,
                            "PR_TITLE": pr_title,
                            "PR_USER": pr_user,
                            "PR_NUM": pr_number,
                            "PR_STATE": pr_state.upper(),
                            "PR_LABELS": pr_labels,
                            "ASSIGNEES": assignees,
                            "MERGED": merged_by,
                            "MILESTONE": milestone,
                            "CHANGES_REQUESTED": changes_requested_by,
                            "APPROVED": approved_by,
                            "HTML_URL": {
                                "link": pr_html_url,
                                "text": "OPEN IN GITHUB",
                            },
                        }
                    }
                    # Update record
                    if lab_slug in records_dicts.keys():
                        r = self.feishu.update_bitable_record(
                            self.app_token,
                            self.table_id,
                            records_dicts[lab_slug],
                            payloads,
                        )
                        print(f"→ Updating {lab_slug} {r['msg'].upper()}")
                    else:
                        # Add record
                        r = self.feishu.add_bitable_record(
                            self.app_token, self.table_id, payloads
                        )
                        print(f"↑ Adding {lab_slug} {r['msg'].upper()}")
                else:
                    print(f"→ Skipping {pr_number} because no index.json found.")
            except Exception as e:
                print(f"Exception: {e}")
                continue


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync Repo PRs to Feishu")
    parser.add_argument("--appid", type=str, help="Feishu App ID")
    parser.add_argument("--appsecret", type=str, help="Feishu App Secret")
    parser.add_argument(
        "--repo", type=str, help="Repo Name like 'labex-dev/devops-labs'"
    )
    parser.add_argument("--ghtoken", type=str, help="GitHub Token")
    args = parser.parse_args()
    main = Sync(app_id=args.appid, app_secret=args.appsecret, ghtoken=args.ghtoken)
    main.sync_pr(repo_name=args.repo)
