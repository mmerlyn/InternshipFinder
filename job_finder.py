import os
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging
import re
import sys

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class CloudJobFinder:
    def __init__(self):
        self.email = os.getenv("EMAIL")
        self.password = os.getenv("EMAIL_PASSWORD") 
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.google_cse_id = os.getenv("GOOGLE_CSE_ID")
        self.send_to = os.getenv("SEND_TO")
        self.custom_query = os.getenv("CUSTOM_QUERY", "")
        self._validate_env_vars()
    
    def _validate_env_vars(self):
        required_vars = {
            "EMAIL": self.email,
            "EMAIL_PASSWORD": self.password,
            "GOOGLE_API_KEY": self.google_api_key,
            "GOOGLE_CSE_ID": self.google_cse_id,
            "SEND_TO": self.send_to
        }
        
        missing_vars = [var for var, value in required_vars.items() if not value]
        if missing_vars:
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        self.recipients = [email.strip() for email in self.send_to.split(',')]
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        invalid_emails = [email for email in self.recipients if not re.match(email_pattern, email)]
        if invalid_emails:
            error_msg = f"Invalid email format(s): {', '.join(invalid_emails)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info(f"Environment variables validated. Recipients: {len(self.recipients)}")
    
    def search_jobs(self):
        try:
            if self.custom_query.strip():
                queries = [self.custom_query.strip()]
                logger.info(f"Using custom search query: {self.custom_query}")
            else:
                queries = [
                    "Spring 2026 Software Engineer internship applications open",
                    "Spring 2026 software internship remote",
                    "Spring 2026 FAANG software internship",
                    "Spring 2026 startup software internship",
                    "Spring 2026 React full stack internship",
                    "Spring 2026 SWE internship hiring now",

                    "2026 Software Engineer Full time applications open",
                    "2026 Software Engineer hiring now",
                    "SDE new grad 2026",
                    "SWE new grad 2026",
                    "software engineer new grad 2026",                  
                    "software developer new grad 2026",
                    "software engineer entry level 2026",
                    "software developer entry level 2026",
                    "tech company new grad software"
                ]
            
            all_results = []
            
            for i, query in enumerate(queries, 1):
                logger.info(f"Search {i}/{len(queries)}: {query}")
                
                if i > 1:
                    import time
                    time.sleep(1)
                
                # Google Custom Search API endpoint
                url = "https://www.googleapis.com/customsearch/v1"
                params = {
                    "key": self.google_api_key,
                    "cx": self.google_cse_id,
                    "q": query,
                    "num": 10,  # Max 10 per request
                    "start": 1
                }
                
                try:
                    response = requests.get(url, params=params, timeout=30)
                    
                    if response.status_code == 429:
                        logger.warning(f"Rate limit hit for query '{query}'. Waiting 5 seconds...")
                        import time
                        time.sleep(5)
                        response = requests.get(url, params=params, timeout=30)
                    
                    response.raise_for_status()
                    data = response.json()

                    if "error" in data:
                        logger.error(f"Google API error: {data['error']}")
                        continue

                    results_count = 0
                    items = data.get("items", [])
                    
                    for item in items:
                        # Filter for job-related URLs
                        url_lower = item.get("link", "").lower()
                        title_lower = item.get("title", "").lower()
                        
                        # More comprehensive job filtering
                        job_indicators = [
                            "careers", "jobs", "job", "internship", "intern", 
                            "apply", "opportunities", "hiring", "employment",
                            "greenhouse", "lever", "workday", "taleo", "bamboohr"
                        ]
                        
                        if any(indicator in url_lower or indicator in title_lower 
                               for indicator in job_indicators):
                            result = {
                                "title": item.get("title", "No title"),
                                "link": item.get("link", ""),
                                "snippet": item.get("snippet", "No description"),
                                "query": query
                            }
                            all_results.append(result)
                            results_count += 1
                    
                    logger.info(f"Found {results_count} job-related results")
                    
                except requests.exceptions.RequestException as e:
                    if "429" in str(e):
                        logger.warning(f"Rate limit exceeded for query '{query}'. Skipping...")
                    else:
                        logger.error(f"API request failed for query '{query}': {e}")
                    continue
            
            logger.info(f"Total raw results collected: {len(all_results)}")
            return self._format_results(all_results)
            
        except Exception as e:
            logger.error(f"Unexpected error during job search: {e}")
            return f"Error searching for jobs: {e}"
    
    def _format_results(self, results):
        if not results:
            return "No internship results found in this search."

        unique_results = {}
        for result in results:
            url = result['link']
            if url and url not in unique_results:
                unique_results[url] = result
        
        logger.info(f"Unique results after deduplication: {len(unique_results)}")

        formatted = f"Fall 2025 SWE Internship Search Results\n"
        formatted += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n"
        formatted += f"Found {len(unique_results)} unique opportunities\n"
        formatted += "=" * 70 + "\n\n"

        key_terms = ["software", "engineer", "developer", "sde", "intern", "2025"]
        sorted_results = sorted(
            unique_results.values(),
            key=lambda x: sum(1 for term in key_terms if term.lower() in x['title'].lower()),
            reverse=True
        )
        
        for i, result in enumerate(sorted_results, 1):
            formatted += f"{i}. {result['title']}\n"

            snippet = result['snippet'][:250] + "..." if len(result['snippet']) > 250 else result['snippet']
            formatted += f"   {snippet}\n"
            formatted += f"   {result['link']}\n"
            formatted += f"   Found via: {result['query']}\n\n"
        
        formatted += f"\nSearch Summary:\n"
        formatted += f"   • Total unique positions: {len(unique_results)}\n"
        formatted += f"   • Search completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        formatted += f"   • Next search: Tomorrow at the same time\n\n"
        formatted += f"Tip: Apply early and customize your applications!\n"
        formatted += f"Automated by GitHub Actions with Google Custom Search API"
        
        return formatted
    
    def send_email(self, body):
        try:
            msg = MIMEMultipart()
            msg["Subject"] = f"Fall 2025 SWE Jobs - {datetime.now().strftime('%m/%d/%Y')}"
            msg["From"] = self.email
            msg["To"] = ", ".join(self.recipients)

            msg.attach(MIMEText(body, "plain"))

            logger.info("Connecting to Gmail SMTP...")
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.email, self.password)
                server.sendmail(self.email, self.recipients, msg.as_string())
            
            logger.info(f"Email sent successfully to {len(self.recipients)} recipient(s)")
            
        except smtplib.SMTPAuthenticationError as e:
            error_msg = "SMTP Authentication failed. Check your email credentials."
            logger.error(f"{error_msg} Details: {e}")
            raise Exception(error_msg)
        except smtplib.SMTPRecipientsRefused as e:
            error_msg = f"Invalid recipient email address(es): {list(e.recipients.keys())}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Email sending failed: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def run(self):
        try:
            logger.info("Starting internship search automation...")
            logger.info(f"Running in: {'GitHub Actions' if os.getenv('GITHUB_ACTIONS') else 'Local environment'}")

            job_results = self.search_jobs()

            logger.info("Sending results via email...")
            self.send_email(job_results)
            
            logger.info("Internship search completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Application failed: {e}")
            with open('error.txt', 'w') as f:
                f.write(f"Error occurred at {datetime.now()}: {str(e)}")
            raise

def main():
    try:
        job_finder = CloudJobFinder()
        success = job_finder.run()
        if success:
            print("Job search automation completed successfully!")
        else:
            print("Job search failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nSearch cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"Application error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()