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

    def get_issues_list(self, repo_name: str) -> list:
        """获取 issues 列表

        Args:
            repo_name (str): 仓库名称
        """
        url = f"https://api.github.com/repos/{repo_name}/issues"
        headers = {
            "Authorization": "token " + self.token,
            "Accept": "application/vnd.github+json",
        }
        params = {
            "state": "all",
            "per_page": 100,
        }

        all_issues = []
        page = 1

        while True:
            params["page"] = page
            print(f"Fetching page {page} of issues...")
            response = requests.get(url, headers=headers, params=params)
            if response.status_code != 200:
                raise Exception(
                    f"Error retrieving issues: {response.status_code}, {response.text}"
                )

            issues = response.json()
            if not issues:
                break

            all_issues.extend(issues)
            page += 1

        # 仅保留 Issue，去掉 PR
        noly_issues = [i for i in all_issues if "pull_request" not in i.keys()]

        return noly_issues


class Sync:
    def __init__(self, app_id: str, app_secret: str, ghtoken: str) -> None:
        self.github = GitHub(token=ghtoken)
        self.feishu = Feishu(app_id, app_secret)
        self.app_token = "bascnNz4Nqjqgqm1Nm5AYke6xxb"
        self.table_id = "tblLnz5UqvvHb5Z0"
        self.skills_table_id = "tblV5pGIsGZMxmE9"

    def sync_issues(self, repo_name: str) -> None:
        # Get all skills from feishu
        skills = self.feishu.get_bitable_records(
            self.app_token, self.skills_table_id, params=""
        )
        # Make a dict of skill and record_id
        skills_dicts = {
            r["fields"]["SKILL_ID"][0]["text"]: r["record_id"] for r in skills
        }
        print(f"Found {len(skills_dicts)} skills in Feishu.")
        # Get all records from feishu
        records = self.feishu.get_bitable_records(
            self.app_token, self.table_id, params=""
        )
        # Make a dict of ISSUE_NUM and record_id
        records_dicts = {r["fields"]["ISSUE_NUM"]: r["record_id"] for r in records}
        # Get all issues from github
        issues_list = self.github.get_issues_list(repo_name)
        print(f"Found {len(issues_list)} issues in GitHub.")
        for issue in issues_list:
            if not issue["locked"]:
                try:
                    issue_title = issue["title"]
                    issue_number = issue["number"]
                    issue_state = issue["state"]
                    issue_user = issue["user"]["login"]
                    issues_html_url = issue["html_url"]
                    # assignees
                    assignees = issue["assignees"]
                    if len(assignees) == 0:
                        assignees = []
                    else:
                        assignees = [a["login"] for a in assignees]
                    # labels
                    issues_labels = issue["labels"]
                    if len(issues_labels) == 0:
                        issues_labels = []
                    else:
                        issues_labels = [l["name"] for l in issues_labels]
                    # skills
                    issues_body = issue["body"]
                    skills = re.findall(r"`\w+/\w+`", issues_body)
                    if len(skills) == 0:
                        skills = []
                    else:
                        skills = [s.replace("`", "").replace(" ", "") for s in skills]
                    # steps
                    steps = re.findall(r"建议步骤数\*\*:(.*[0-9])", issues_body)
                    if len(steps) == 0:
                        steps_num = 0
                    else:
                        try:
                            steps_num = int(steps[0].strip())
                        except:
                            steps_num = 0
                    # search skills in feishu
                    skills_record_ids = []
                    for skill in skills:
                        if skill in skills_dicts.keys():
                            skills_record_ids.append(skills_dicts[skill])
                    # payloads
                    payloads = {
                        "fields": {
                            "ISSUE_TITLE": issue_title,
                            "ISSUE_NUM": issue_number,
                            "ISSUE_STATE": issue_state.upper(),
                            "ISSUE_USER": issue_user,
                            "ISSUE_STEPS": steps_num,
                            "HTML_URL": {
                                "link": issues_html_url,
                                "text": "OPEN IN GITHUB",
                            },
                            "ASSIGNEES": assignees,
                            "ISSUE_LABELS": issues_labels,
                            "SCENARIO_SKILLS": skills_record_ids,
                            "SKILLS": skills,
                            "ISSUE_BODY": issues_body,
                        }
                    }
                    # Update record
                    if str(issue_number) in records_dicts.keys():
                        r = self.feishu.update_bitable_record(
                            self.app_token,
                            self.table_id,
                            records_dicts[str(issue_number)],
                            payloads,
                        )
                        print(f"→ Updating {issue_title} {r['msg'].upper()}")
                    else:
                        # Add record
                        r = self.feishu.add_bitable_record(
                            self.app_token, self.table_id, payloads
                        )
                        print(f"↑ Adding {issue_title} {r['msg'].upper()}")

                except Exception as e:
                    print(f"Exception: {e}")
                    continue
            else:
                print(f"Locked: {issue['title']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync Repo Issues to Feishu")
    parser.add_argument("--appid", type=str, help="Feishu App ID")
    parser.add_argument("--appsecret", type=str, help="Feishu App Secret")
    parser.add_argument(
        "--repo", type=str, help="Repo Name like 'labex-dev/devops-labs'"
    )
    parser.add_argument("--ghtoken", type=str, help="GitHub Token")
    args = parser.parse_args()
    main = Sync(app_id=args.appid, app_secret=args.appsecret, ghtoken=args.ghtoken)
    main.sync_issues(repo_name=args.repo)
