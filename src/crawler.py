import requests
import time
import json
import base64
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from tqdm import tqdm
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config
from src.database import DatabaseManager
from src.models import Repository, CrawlMetadata

class GitHubCrawler:
    def __init__(self):
        print(" Initializing GitHub Crawler...")
        self.db = DatabaseManager()
        self.headers = {
            "Authorization": f"Bearer {Config.GITHUB_TOKEN}",
            "Content-Type": "application/json"
        }
        self.rate_limit_remaining = Config.RATE_LIMIT_POINTS
        self.rate_limit_reset = None
        self.total_fetched = 0
    
        if not Config.GITHUB_TOKEN or Config.GITHUB_TOKEN == "your_github_token_here":
            print(" ERROR: GitHub token not set!")
            print("Please create a .env file with GITHUB_TOKEN=your_token")
            print("Get token from: https://github.com/settings/tokens")
            sys.exit(1)
    
    def _extract_github_id(self, graphql_id: str) -> int:
        """
        Extract numeric GitHub ID from GraphQL ID.
        Fallback method if databaseId is not available.
        """
        if not graphql_id:
            return 0
        
        try:
            import re
            numbers = re.findall(r'\d+', graphql_id)
            if numbers:
                return int(max(numbers, key=len))
 
            return abs(hash(graphql_id)) % (10**12)
        except:
            return abs(hash(str(graphql_id))) % (10**12)
    
    def make_graphql_request(self, query: str, variables: Dict = None) -> Optional[Dict]:
        """Make GraphQL request with retry logic"""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        for attempt in range(Config.MAX_RETRIES):
            try:
                response = requests.post(
                    Config.GITHUB_GRAPHQL_URL,
                    json=payload,
                    headers=self.headers,
                    timeout=Config.REQUEST_TIMEOUT
                )

                if 'X-RateLimit-Remaining' in response.headers:
                    self.rate_limit_remaining = int(response.headers['X-RateLimit-Remaining'])
                if 'X-RateLimit-Reset' in response.headers:
                    reset_timestamp = int(response.headers['X-RateLimit-Reset'])
                    self.rate_limit_reset = datetime.fromtimestamp(reset_timestamp)
                
                if response.status_code == 200:
                    data = response.json()
   
                    if "errors" in data:
                        error_msg = data['errors'][0]['message'] if data['errors'] else 'Unknown'
                        print(f" GraphQL Error: {error_msg}")
                        if "rate limit" in error_msg.lower():
                            wait_time = 60
                            print(f" Rate limited. Waiting {wait_time} seconds...")
                            time.sleep(wait_time)
                            continue
                        return None
                    
                    return data
                    
                elif response.status_code == 429:  
                    retry_after = int(response.headers.get('Retry-After', 60))
                    print(f" Rate limited. Retrying after {retry_after} seconds...")
                    time.sleep(retry_after)
                    
                elif response.status_code == 401:  
                    print(" Invalid GitHub token. Please check your GITHUB_TOKEN")
                    return None
                    
                elif response.status_code == 403: 
                    print(" Rate limit exceeded. Waiting for reset...")
                    if self.rate_limit_reset:
                        wait_seconds = (self.rate_limit_reset - datetime.now()).total_seconds()
                        if wait_seconds > 0:
                            wait_time = min(wait_seconds + 10, 300)  
                            print(f"Waiting {int(wait_time)} seconds...")
                            time.sleep(wait_time)
                    else:
                        time.sleep(300)  
                        
                else:
                    print(f" HTTP {response.status_code}: {response.text[:200]}")
                    time.sleep(Config.RETRY_DELAY * (attempt + 1))
                    
            except requests.exceptions.RequestException as e:
                print(f" Request error (attempt {attempt + 1}): {e}")
                time.sleep(Config.RETRY_DELAY * (attempt + 1))
        
        print(" Max retries exceeded")
        return None
    
    def fetch_repositories_batch(self, cursor: str = None) -> Dict:
        """Fetch one batch of repositories (up to 100)"""
        query = """
        query ($cursor: String) {
          search(
            query: "stars:>1 sort:stars-desc"
            type: REPOSITORY
            first: 100
            after: $cursor
          ) {
            pageInfo {
              hasNextPage
              endCursor
            }
            nodes {
              ... on Repository {
                databaseId
                name
                nameWithOwner
                owner {
                  login
                }
                stargazerCount
                createdAt
                updatedAt
                isArchived
                primaryLanguage {
                  name
                }
                forkCount
                issues(states: OPEN) {
                  totalCount
                }
                diskUsage
              }
            }
          }
          rateLimit {
            remaining
            resetAt
          }
        }
        """
        
        variables = {"cursor": cursor} if cursor else {}
        data = self.make_graphql_request(query, variables)
        
        if not data:
            return {"repositories": [], "has_next_page": False, "end_cursor": None}
        
        search_data = data.get("data", {}).get("search", {})
        rate_limit = data.get("data", {}).get("rateLimit", {})
        
        if rate_limit:
            self.rate_limit_remaining = rate_limit.get("remaining", self.rate_limit_remaining)
        
        repositories = []
        nodes = search_data.get("nodes", [])
        
        for node in nodes:
            if not node:
                continue  
            
            try:
                github_id = node.get("databaseId")
                if not github_id:
                    print(f" No databaseId for repository, skipping")
                    continue
          
                owner = node.get("owner", {})
                primary_language = node.get("primaryLanguage", {})
                issues = node.get("issues", {})
                
                repo = {
                    "github_id": github_id,
                    "name": node.get("name", ""),
                    "full_name": node.get("nameWithOwner", ""),
                    "owner_login": owner.get("login", "") if owner else "",
                    "stargazers_count": node.get("stargazerCount", 0),
                    "created_at": node.get("createdAt"),
                    "updated_at": node.get("updatedAt"),
                    "archived": node.get("isArchived", False),
                    "language": primary_language.get("name") if primary_language else None,
                    "forks_count": node.get("forkCount", 0),
                    "open_issues_count": issues.get("totalCount", 0) if issues else 0,
                    "size_kb": node.get("diskUsage", 0)  
                }
                repositories.append(repo)
            except Exception as e:
                print(f" Error processing repository node: {e}")
                continue
        
        page_info = search_data.get("pageInfo", {})
        return {
            "repositories": repositories,
            "has_next_page": page_info.get("hasNextPage", False),
            "end_cursor": page_info.get("endCursor")
        }
    
    def save_batch_to_db(self, batch: List[Dict]):
        """Save or update a batch of repositories"""
        try:
            for repo_data in batch:
                if not repo_data.get("github_id"):
                    continue
 
                existing = self.db.session.query(Repository).filter_by(
                    github_id=repo_data["github_id"]
                ).first()
                
                if existing:
                    update_needed = False
                    if existing.stargazers_count != repo_data["stargazers_count"]:
                        existing.stargazers_count = repo_data["stargazers_count"]
                        update_needed = True

                    updated_at_str = repo_data["updated_at"]
                    if updated_at_str:
                        try:
                            updated_at_dt = datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))
                            if existing.updated_at != updated_at_dt:
                                existing.updated_at = updated_at_dt
                                update_needed = True
                        except:
                            pass
                    
                    if update_needed:
                        existing.last_crawled = datetime.utcnow()
                else:
                    created_at = None
                    updated_at = None
                    
                    try:
                        if repo_data["created_at"]:
                            created_at = datetime.fromisoformat(repo_data["created_at"].replace('Z', '+00:00'))
                        if repo_data["updated_at"]:
                            updated_at = datetime.fromisoformat(repo_data["updated_at"].replace('Z', '+00:00'))
                    except:
                        pass
                    
                    repo = Repository(
                        github_id=repo_data["github_id"],
                        name=repo_data["name"],
                        full_name=repo_data["full_name"],
                        owner_login=repo_data["owner_login"],
                        stargazers_count=repo_data["stargazers_count"],
                        created_at=created_at,
                        updated_at=updated_at,
                        archived=repo_data["archived"],
                        language=repo_data["language"],
                        forks_count=repo_data["forks_count"],
                        open_issues_count=repo_data["open_issues_count"],
                        size_kb=repo_data["size_kb"],
                        last_crawled=datetime.utcnow()
                    )
                    self.db.session.add(repo)
            
            self.db.session.commit()
            
        except Exception as e:
            self.db.session.rollback()
            print(f" Error saving batch to database: {type(e).__name__}: {e}")

    def run(self):
        """Main execution method"""
        print(f" Target: Fetch {Config.TOTAL_REPOS} repositories")
        print(f" GitHub token configured: Yes")
        
        cursor = None
        has_next_page = True
        batch_count = 0

        pbar = tqdm(total=Config.TOTAL_REPOS, desc="Crawling repositories")
        
        try:
            while has_next_page and self.total_fetched < Config.TOTAL_REPOS:
                if self.rate_limit_remaining < 50:
                    print(f" Rate limit low ({self.rate_limit_remaining} remaining)")
                    if self.rate_limit_reset:
                        wait_seconds = (self.rate_limit_reset - datetime.now()).total_seconds()
                        if wait_seconds > 0:
                            wait_time = min(wait_seconds + 10, 300)  
                            print(f" Waiting {int(wait_time)} seconds for rate limit reset...")
                            time.sleep(wait_time)
                    else:
                        time.sleep(60)
     
                result = self.fetch_repositories_batch(cursor)
                
                if not result["repositories"]:
                    print(" No repositories returned in batch. Stopping.")
                    break
     
                self.save_batch_to_db(result["repositories"])

                batch_size = len(result["repositories"])
                self.total_fetched += batch_size
                batch_count += 1
  
                pbar.update(batch_size)
                pbar.set_postfix({
                    "Batch": batch_count,
                    "Rate Limit": self.rate_limit_remaining,
                    "Total": self.total_fetched
                })

                has_next_page = result["has_next_page"]
                cursor = result["end_cursor"]

                time.sleep(0.5)
    
                if self.total_fetched % Config.SAVE_INTERVAL == 0:
                    print(f" Progress: {self.total_fetched}/{Config.TOTAL_REPOS} repositories saved")
            
            pbar.close()

            metadata = CrawlMetadata(
                total_repos_crawled=self.total_fetched,
                last_crawl_end=datetime.utcnow(),
                rate_limit_remaining=self.rate_limit_remaining,
                rate_limit_reset=self.rate_limit_reset
            )
            self.db.session.add(metadata)
            self.db.session.commit()
            
            print(f"\n Successfully crawled {self.total_fetched} repositories!")
            print(f" Final rate limit remaining: {self.rate_limit_remaining}")
            
        except KeyboardInterrupt:
            print("\n Crawling interrupted by user")
            pbar.close()
        except Exception as e:
            print(f"\n Error during crawling: {type(e).__name__}: {e}")
            pbar.close()
            raise
        finally:
            self.db.close()

if __name__ == "__main__":
    crawler = GitHubCrawler()
    crawler.run()